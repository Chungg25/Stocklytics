from app.ai.llm_client import get_orca_client, ORCA_MODEL

import os
import requests
from datetime import datetime, timedelta
from app.db import supabase

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

def fetch_stock_news(ticker: str) -> list:
    """Fetch latest news for a stock using Finnhub and cache in Supabase."""
    try:
        # 1. Fetch from Finnhub if API key is present
        if FINNHUB_API_KEY:
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
            
            resp = requests.get(url)
            if resp.status_code == 200:
                articles = resp.json()
                
                # Insert top 20 into Supabase (upsert based on URL isn't natively supported in standard insert without RPC, 
                # but we can try to insert and ignore errors, or just insert if they don't exist.
                # Actually, standard supabase-py has upsert. Let's use upsert if we had primary keys setup correctly.
                # Since 'url' is UNIQUE, we can try to insert one by one or filter. 
                # To keep it simple and robust, we fetch current URLs from DB first.
                
                # We will limit to 10 to avoid huge payloads
                articles = articles[:15]
                
                for article in articles:
                    try:
                        # Convert unix timestamp to ISO
                        pub_date = datetime.fromtimestamp(article.get('datetime', 0)).isoformat()
                        
                        supabase.table('stock_news').insert({
                            "ticker": ticker,
                            "title": article.get("headline", ""),
                            "url": article.get("url", ""),
                            "source": article.get("source", ""),
                            "summary": article.get("summary", ""),
                            "published_at": pub_date
                        }).execute()
                    except Exception as e:
                        # Likely unique constraint violation on url, ignore
                        pass

        # 2. Fetch from Supabase (Always fetch from DB to return to client)
        res = supabase.table('stock_news').select('*').eq('ticker', ticker).order('published_at', desc=True).limit(10).execute()
        
        if res.data:
            results = []
            for r in res.data:
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("summary", ""),
                    "source": r.get("source", ""),
                    "url": r.get("url", ""),
                    "date": r.get("published_at", "")[:10],
                    "image": "" # Finnhub has image, but we didn't add it to schema. We can ignore or add later.
                })
            return results
            
        return []
    except Exception as e:
        print(f"News fetch failed: {e}")
        return []

def summarize_and_rate_news(ticker: str, articles: list) -> dict:
    """Use AI to summarize news articles and rate sentiment."""
    if not articles:
        return {"summary": "No recent news found.", "sentiment": "neutral", "articles": []}
    
    articles_text = "\n\n".join([
        f"Title: {a['title']}\nSource: {a['source']}\nDate: {a['date']}\nBody: {a['body'][:300]}"
        for a in articles[:6]
    ])
    
    prompt = f"""You are a financial news analyst. Analyze these recent news articles about {ticker} stock.

{articles_text}

Respond in this EXACT JSON format:
{{
    "summary": "2-3 sentence overall summary of the news sentiment and key events",
    "sentiment": "bullish" or "bearish" or "neutral",
    "sentiment_score": 0-100 (0=very bearish, 50=neutral, 100=very bullish),
    "key_events": ["event 1", "event 2", "event 3"],
    "rated_articles": [
        {{"title": "...", "impact": "positive" or "negative" or "neutral", "reason": "brief reason"}}
    ]
}}
Only output raw JSON, no markdown."""

    try:
        client = get_orca_client()
        response = client.chat.completions.create(
            model=ORCA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        import re
        content = response.choices[0].message.content
        # Clean up potential markdown wrapping
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        result = json.loads(content)
        result["articles"] = articles
        return result
    except Exception as e:
        print(f"News summarization failed: {e}")
        return {
            "summary": f"Found {len(articles)} recent articles about {ticker}.",
            "sentiment": "neutral",
            "sentiment_score": 50,
            "articles": articles
        }
