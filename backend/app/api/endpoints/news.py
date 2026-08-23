from fastapi import APIRouter
from app.services.news_service import fetch_stock_news, summarize_and_rate_news

router = APIRouter()

@router.get("/{ticker}")
def get_stock_news(ticker: str):
    """Fetch latest news for a given stock ticker."""
    try:
        articles = fetch_stock_news(ticker.upper())
        return {"status": "success", "data": articles}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/{ticker}/summary")
def get_news_summary(ticker: str):
    """Fetch news and return AI-powered summary with sentiment analysis."""
    try:
        articles = fetch_stock_news(ticker.upper())
        result = summarize_and_rate_news(ticker.upper(), articles)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
