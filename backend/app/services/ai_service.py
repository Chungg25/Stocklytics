import os
import json
from dotenv import load_dotenv
from openai import OpenAI

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

def execute_with_fallback(messages, response_format=None):
    client, key_idx = get_groq_client()
    if not client:
        raise Exception("No Groq API keys found in .env")
        
    try:
        kwargs = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str or "quota" in error_str or "insufficient" in error_str:
            print(f"Key {key_idx} failed with rate limit/quota. Switching key...")
            switch_key()
            client2, _ = get_groq_client()
            kwargs["model"] = "llama-3.3-70b-versatile"
            response = client2.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        raise e



def generate_ai_analysis(tickers, prompt):
    if not tickers:
        return "Please select at least one stock to analyze."
    
    tickers_str = ", ".join(tickers)
    full_prompt = (
        f"You are an expert financial analyst. Please analyze the following stocks: {tickers_str}.\n\n"
        f"User Query: {prompt}\n\n"
        "Please provide a comprehensive, markdown-formatted response. Please search the web for the latest information and cite your sources."
    )

    try:
        client = get_zhipu_client()
        response = client.chat.completions.create(
            model="z-ai/glm-4.7-flash-free",
            messages=[{"role": "user", "content": full_prompt}],
            tools=[{"type": "web_search", "web_search": {"enable": True}}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"**Error during AI Analysis:**\n\n```\n{str(e)}\n```"

def generate_ai_assessment(ticker: str, mode: str, user_prompt: str = ""):
    file_map = {
        "checklist": "investment-checklist.md",
        "research": "investment-research.md",
        "team": "investment-team.md"
    }
    file_name = file_map.get(mode, "investment-checklist.md")
    
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "skill", file_name)
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        return f"Could not load skill file {file_name}: {e}"
        
    full_prompt = template.replace("$ARGUMENTS", ticker)
    
    full_prompt += f"\n\n[FINAL SYSTEM DIRECTIVE]\n1. You MUST write your ENTIRE response in ENGLISH, regardless of the user's prompt. Translate all your analysis, headers, and bullet points into ENGLISH. This is a strict requirement.\n2. IMPORTANT: You MUST use your own native web_search tool to find the absolute latest real-time financial data, news and events about this company to supplement your analysis. ALWAYS cite your sources as links at the end of your report."

    try:
        client = get_zhipu_client()
        response = client.chat.completions.create(
            model="z-ai/glm-4.7-flash-free",
            messages=[{"role": "user", "content": full_prompt}],
            tools=[{"type": "web_search", "web_search": {"enable": True}}],
            stream=True
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        yield f"**Error during AI Assessment:**\n\n```\n{str(e)}\n```"

def parse_ai_intent(user_prompt: str):
    system_prompt = """
    You are an intent parser for a financial charting app. The user will provide a natural language prompt. 
    You must return a STRICT JSON object representing their intent. Do NOT return any markdown formatting, only raw JSON.
    
    Format:
    {
      "target_ticker": "AAPL", // The stock ticker they want to look at, or null if none mentioned
      "indicators": ["RSI", "MACD"], // Array of technical indicator acronyms they want to add (e.g. RSI, MACD, EMA, SMA, BB, Volume). Or empty array.
      "find_peers": false // Boolean. True if they want to compare or find competitors/peers in the same sector.
    }
    """

    try:
        content = execute_with_fallback([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], response_format={"type": "json_object"})
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}
