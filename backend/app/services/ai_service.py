import json
from app.ai.llm_client import get_zhipu_client, execute_with_fallback, get_active_key_status
from app.ai.prompts import build_assessment_prompt

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

def generate_ai_assessment(ticker: str, mode: str, user_prompt: str = "", context: str = ""):
    full_prompt = build_assessment_prompt(ticker, mode, context)

    try:
        if mode in ["tradingagents", "tradingagents_fast"]:
            # Use Groq Llama for trading agents to get faster/better JSON parsing
            response_stream = execute_with_fallback(
                messages=[{"role": "user", "content": full_prompt}], 
                stream=True
            )
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
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
