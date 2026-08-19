import yfinance as yf
from app.ai.tools import tool
from typing import List, Dict, Any

@tool(
    name="compare_multiple_stocks",
    description="Compare multiple stock tickers based on key financial metrics like P/E, EPS, Revenue Growth, and Margins.",
    parameters={
        "type": "object",
        "properties": {
            "tickers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of stock tickers to compare (e.g., ['AAPL', 'MSFT', 'GOOGL'])"
            }
        },
        "required": ["tickers"]
    }
)
def compare_multiple_stocks(tickers: List[str]) -> Dict[str, Any]:
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            results.append({
                "ticker": ticker,
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "trailingEps": info.get("trailingEps"),
                "revenueGrowth": info.get("revenueGrowth"),
                "profitMargins": info.get("profitMargins")
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
            
    return {
        "comparison_data": results,
        "source": "Yahoo Finance",
        "url": "https://finance.yahoo.com"
    }
