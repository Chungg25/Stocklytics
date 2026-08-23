import json
import yfinance as yf
from app.ai.llm_client import get_orca_client, execute_with_fallback, get_active_key_status, ORCA_MODEL
from app.ai.prompts import build_assessment_prompt
from app.services.news_service import fetch_stock_news

def generate_ai_analysis(tickers, prompt):
    if not tickers:
        return "Please select at least one stock to analyze."
    
    tickers_str = ", ".join(tickers)
    full_prompt = (
        f"You are an expert financial analyst. Please analyze the following stocks: {tickers_str}.\n\n"
        f"User Query: {prompt}\n\n"
        "Please provide a comprehensive, markdown-formatted response with the latest information. Cite your sources."
    )

    try:
        client = get_orca_client()
        response = client.chat.completions.create(
            model=ORCA_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"**Error during AI Analysis:**\n\n```\n{str(e)}\n```"

def generate_ai_assessment(ticker: str, mode: str, user_prompt: str = "", context: str = ""):
    # Fetch real-time context (News + Tech Indicators)
    try:
        # Fetch News
        news = fetch_stock_news(ticker)
        news_text = "No recent news."
        if news:
            news_text = "\n".join([f"- {n['title']} ({n['date']})" for n in news[:5]])
        
        # Fetch Indicators
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        tech_text = "No technical data."
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            high52 = hist['High'].max()
            low52 = hist['Low'].min()
            vol = hist['Volume'].iloc[-1]
            tech_text = f"Current Price: {current_price:.2f}\n50-Day MA: {ma50:.2f}\n200-Day MA: {ma200:.2f}\n52-Week High: {high52:.2f}\n52-Week Low: {low52:.2f}\nLatest Volume: {vol}"
            
        enriched_context = f"{context}\n\n[LATEST NEWS]\n{news_text}\n\n[TECHNICAL INDICATORS]\n{tech_text}"
    except Exception as e:
        enriched_context = context
        print(f"Failed to fetch enriched context: {e}")

    full_prompt = build_assessment_prompt(ticker, mode, enriched_context)

    try:
        client = get_orca_client()
        response = client.chat.completions.create(
            model=ORCA_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
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
