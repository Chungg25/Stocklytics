"""
Reusable @tool wrappers for the agent pipeline.
Exposes DataCollector, Calculator, Scoring, and full UC1 analysis as LLM-callable tools.
"""

from app.ai.tools import tool
from typing import Dict, Any


@tool(
    name="collect_stock_data",
    description="Collect comprehensive stock data (price, fundamentals, technicals, news, analyst consensus) for a ticker. Returns raw data used by other analysis tools.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
            }
        },
        "required": ["ticker"]
    }
)
def collect_stock_data(ticker: str) -> Dict[str, Any]:
    from app.agents.data_collector import collect
    result = collect(ticker)
    if "error" not in result:
        result.pop("history_1y", None)
    return result


@tool(
    name="calculate_stock_metrics",
    description="Calculate financial metrics (DCF valuation, Piotroski F-Score, Altman Z-Score, technical indicators, growth, risk) from raw stock data. Requires output from collect_stock_data.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol"
            }
        },
        "required": ["ticker"]
    }
)
def calculate_stock_metrics(ticker: str) -> Dict[str, Any]:
    from app.agents.data_collector import collect
    from app.agents.calculator import calculate
    raw_data = collect(ticker)
    if "error" in raw_data:
        return raw_data
    return calculate(raw_data)


@tool(
    name="score_stock",
    description="Score a stock on a 0-100 scale across 4 pillars: Fundamentals (30%), Technical (25%), Sentiment (25%), Value (20%). Returns rating (BUY/HOLD/SELL) and confidence level.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol"
            }
        },
        "required": ["ticker"]
    }
)
def score_stock(ticker: str) -> Dict[str, Any]:
    from app.agents.data_collector import collect
    from app.agents.calculator import calculate
    from app.agents.scoring import score
    raw_data = collect(ticker)
    if "error" in raw_data:
        return raw_data
    calc_result = calculate(raw_data)
    if "error" in calc_result:
        return calc_result
    return score(calc_result, raw_data)


@tool(
    name="full_stock_analysis",
    description="Run the complete UC1 analysis pipeline: data collection, financial calculations, scoring, and 4 Masters AI perspectives (Duan Yongping, Buffett, Munger, Li Lu). Returns comprehensive investment analysis with thesis, bull/bear cases, and price scenarios.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol"
            }
        },
        "required": ["ticker"]
    }
)
def full_stock_analysis(ticker: str) -> Dict[str, Any]:
    from app.agents.orchestrator import analyze_stock
    return analyze_stock(ticker, save=False)


@tool(
    name="suggest_stocks",
    description="Screen the ~130-stock universe with preset filters (quality_growth, value, growth, momentum, dividend_safety) and return top stock picks with AI-generated thesis, entry/stop-loss/target prices, portfolio allocation, and diversification analysis. Optionally filter by theme (ai, cloud, energy, dividend, etc.).",
    parameters={
        "type": "object",
        "properties": {
            "screen": {
                "type": "string",
                "description": "Screening preset: quality_growth, value, growth, momentum, dividend_safety (default: quality_growth)"
            },
            "theme": {
                "type": "string",
                "description": "Optional thematic filter: ai, cloud, cybersecurity, ev, healthcare_innovation, energy, dividend, fintech"
            },
            "max_picks": {
                "type": "integer",
                "description": "Maximum picks to return (1-15, default 8)"
            }
        },
        "required": []
    }
)
def suggest_stocks(screen: str = "quality_growth", theme: str = None, max_picks: int = 8) -> Dict[str, Any]:
    from app.agents.suggester import suggest
    return suggest(screen=screen, theme=theme, max_picks=max_picks)


@tool(
    name="compare_stocks",
    description="Compare 2-5 stocks side by side with rankings, anomaly detection, correlation matrix, historical performance, and normalized chart data. Pass a single ticker to auto-find industry peers. AI picks 'best for' growth, value, risk/reward, and diversification.",
    parameters={
        "type": "object",
        "properties": {
            "tickers": {
                "type": "string",
                "description": "Comma-separated ticker symbols (e.g., 'NVDA,AMD,AVGO'). Single ticker auto-finds peers."
            }
        },
        "required": ["tickers"]
    }
)
def compare_stocks(tickers: str) -> Dict[str, Any]:
    from app.agents.comparator import compare
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    auto_peers = len(ticker_list) == 1
    return compare(ticker_list, auto_peers=auto_peers)
