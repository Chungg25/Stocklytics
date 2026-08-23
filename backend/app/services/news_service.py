from app.ai.llm_client import get_orca_client, ORCA_MODEL

def fetch_stock_news(ticker: str) -> list:
    """Fetch latest news for a stock using DuckDuckGo search."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(f"{ticker} stock news", max_results=8):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "source": r.get("source", ""),
                    "url": r.get("url", ""),
                    "date": r.get("date", ""),
                    "image": r.get("image", "")
                })
        return results
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
