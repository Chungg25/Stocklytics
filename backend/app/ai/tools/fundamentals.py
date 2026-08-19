import yfinance as yf
from app.ai.tools import tool

@tool(
    name="get_stock_fundamentals",
    description="Get core financial projections (Revenue, EPS) and trailing metrics for a stock.",
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
def get_stock_fundamentals(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "ticker": ticker,
            "revenue": {
                "trailing": info.get("totalRevenue"),
                "revenueGrowth": info.get("revenueGrowth")
            },
            "eps": {
                "trailing": info.get("trailingEps"),
                "forward": info.get("forwardEps")
            },
            "valuation": {
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "priceToBook": info.get("priceToBook")
            },
            "source": "Yahoo Finance",
            "url": f"https://finance.yahoo.com/quote/{ticker}"
        }
    except Exception as e:
        return {"error": f"Failed to fetch fundamentals for {ticker}: {str(e)}"}
