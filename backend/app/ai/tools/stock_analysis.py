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
