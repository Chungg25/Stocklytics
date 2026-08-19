import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Global state to track which key is currently active
ACTIVE_KEY_INDEX = 1

def get_groq_client():
    global ACTIVE_KEY_INDEX
    key1 = os.getenv("GROQ_API_KEY_1")
    key2 = os.getenv("GROQ_API_KEY_2")
    
    if ACTIVE_KEY_INDEX == 1 and key1:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key1), 1
    elif ACTIVE_KEY_INDEX == 2 and key2:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key2), 2
    elif key1: # Fallback if only key 1 exists but index was 2
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key1), 1
    elif key2:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key2), 2
    return None, 0

def get_zhipu_client():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise Exception("Zenmux API_KEY is missing in .env")
    return OpenAI(base_url="https://zenmux.ai/api/v1", api_key=api_key)

def switch_key():
    global ACTIVE_KEY_INDEX
    ACTIVE_KEY_INDEX = 2 if ACTIVE_KEY_INDEX == 1 else 1

def get_active_key_status():
    return ACTIVE_KEY_INDEX

def execute_with_fallback(messages, response_format=None, stream=False, tools=None):
    client, key_idx = get_groq_client()
    if not client:
        raise Exception("No Groq API keys found in .env")
        
    try:
        kwargs = {
            "model": "qwen/qwen3.6-27b",
            "messages": messages,
            "stream": stream
        }
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
            
        response = client.chat.completions.create(**kwargs)
        if stream:
            return response
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            print(f"Groq rate limit hit. Switching key...")
            switch_key()
            client2, _ = get_groq_client()
            kwargs["model"] = "qwen/qwen3.6-27b"
            response = client2.chat.completions.create(**kwargs)
            if stream:
                return response
            return response.choices[0].message.content
        raise e

def summarize_large_payload(payload: str) -> str:
    """Uses the 2nd Groq API key to summarize large payloads to save the 1st key's TPM limit."""
    key2 = os.getenv("GROQ_API_KEY_2")
    if not key2:
        return payload[:2000] + "... [TRUNCATED DUE TO NO 2ND KEY]"
        
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key2)
        
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {"role": "system", "content": "You are a financial data compressor. Given a large JSON dump from a financial tool, summarize it into a compact, highly dense summary containing only the most critical numbers, trends, and facts. Output purely the summary data without conversational padding."},
                {"role": "user", "content": f"Compress this data:\n{payload}"}
            ],
            max_tokens=800
        )
        import re
        result_content = response.choices[0].message.content
        # Remove <think>...</think> reasoning blocks if present
        clean_content = re.sub(r'<think>.*?</think>', '', result_content, flags=re.DOTALL).strip()
        return clean_content
    except Exception as e:
        print(f"Summarizer failed: {e}")
        # Ultimate fallback if summarizer also fails
        return payload[:2000] + "... [TRUNCATED DUE TO ERROR]"
