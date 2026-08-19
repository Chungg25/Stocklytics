import json
from app.ai.tools import tool

@tool(
    name="web_search_with_citations",
    description="Search the web for recent news, catalysts, or risks about a stock. Returns text with citations.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query, e.g., 'AAPL recent news 2024' or 'GOOGL AI risks'"
            }
        },
        "required": ["query"]
    }
)
def web_search_with_citations(query: str) -> dict:
    """
    Real web search using DuckDuckGo.
    """
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=4):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "source": r.get("title", "").split("|")[-1].strip(),
                    "url": r.get("href", "")
                })
        return {"results": results}
    except Exception as e:
        return {"error": f"Search failed: {e}", "results": []}


@tool(
    name="get_wall_street_targets",
    description="Get the latest Wall Street consensus targets and bank predictions for a stock ticker.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol (e.g., AAPL)"
            }
        },
        "required": ["ticker"]
    }
)
def get_wall_street_targets(ticker: str) -> dict:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker,
            "consensus_rating": info.get("recommendationKey", "N/A"),
            "average_target": info.get("targetMeanPrice", "N/A"),
            "high_target": info.get("targetHighPrice", "N/A"),
            "low_target": info.get("targetLowPrice", "N/A"),
            "current_price": info.get("currentPrice", "N/A"),
            "analyst_count": info.get("numberOfAnalystOpinions", "N/A")
        }
    except Exception as e:
        return {"error": f"Failed to fetch target: {e}"}
