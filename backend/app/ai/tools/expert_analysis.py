from app.ai.tools import tool
from typing import Dict, Any

@tool(
    name="run_expert_analysis_tool",
    description="Run the 4-team expert analysis (Business, Financial, Industry, Risk) for a specific stock to get projected price scenarios and insights.",
    parameters={
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The stock ticker symbol"
            }
        },
        "required": ["ticker"]
    }
)
def run_expert_analysis_tool(ticker: str) -> Dict[str, Any]:
    """
    Calls an internal Sub-LLM to act as the 4-Agent investment team 
    and output a synthesized report with target scenarios.
    """
    try:
        from app.ai.llm_client import execute_with_fallback
        import yfinance as yf
        import json
        
        # Gather basic data to feed the sub-LLM
        stock = yf.Ticker(ticker)
        info = stock.info
        
        current_price = info.get("currentPrice", "N/A")
        revenue_growth = info.get("revenueGrowth", "N/A")
        margins = info.get("profitMargins", "N/A")
        
        from datetime import datetime
        current_year = datetime.now().year
        
        system_prompt = f"""You are the Stocklytics Expert Team (Business, Financial, Industry, Risk).
Current Year: {current_year}.
Analyze {ticker}. Current Price: {current_price}, Rev Growth: {revenue_growth}, Margins: {margins}.
Output your analysis strictly in this JSON format:
{{
  "ticker": "{ticker}",
  "team_analysis": {{
    "business_model": "str", "financials": "str", "industry": "str", "risk_mgmt": "str"
  }},
  "target_scenarios": [
    {{"scenario": "Conservative", "price": float, "logic": "str"}},
    {{"scenario": "Base Case", "price": float, "logic": "str"}},
    {{"scenario": "Bull Case", "price": float, "logic": "str"}},
    {{"scenario": "Very Bullish", "price": float, "logic": "str"}}
  ]
}}"""
        
        response = execute_with_fallback(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Generate the 4-dimension report for {ticker}."}],
            response_format={"type": "json_object"},
            stream=False
        )
        
        parsed_result = json.loads(response)
        parsed_result["source"] = "Internal Sub-LLM Analysis"
        return parsed_result
        
    except Exception as e:
        return {"error": f"Expert Analysis failed: {e}"}
