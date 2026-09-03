"""
OrchestratorAgent — UC1 Entry Point
Chains: DataCollector → Calculator → Scoring → Analyst → TrackRecord
"""

from datetime import datetime
from app.agents.data_collector import collect
from app.agents.calculator import calculate
from app.agents.scoring import score
from app.agents.analyst import analyze


def _save_to_db(ticker: str, result: dict, user_id: str = None):
    try:
        from app.db import supabase
        if not supabase or not user_id:
            return None

        synthesis = result.get("synthesis", {})
        score_data = result.get("score", {})

        record = {
            "user_id": user_id,
            "ticker": ticker,
            "action": synthesis.get("decision", "Gray Zone"),
            "reasoning": synthesis.get("summary", ""),
            "ai_score": score_data.get("total_score"),
            "ai_rating": score_data.get("rating"),
            "price_at_decision": result.get("price", {}).get("current"),
        }

        resp = supabase.table("ai_decisions").insert(record).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


def analyze_stock(ticker: str, user_id: str = None, save: bool = True) -> dict:
    """
    UC1 full pipeline. Returns structured analysis result.
    """
    ticker = ticker.upper().strip()

    # Step 1: Collect raw data
    raw_data = collect(ticker)
    if "error" in raw_data:
        return {"error": raw_data["error"], "ticker": ticker}

    # Step 2: Calculate financial metrics
    calc_result = calculate(raw_data)
    if "error" in calc_result:
        return {"error": calc_result["error"], "ticker": ticker}

    # Step 3: Score (deterministic)
    score_result = score(calc_result, raw_data)

    # Step 4: LLM analysis (4 Masters + synthesis)
    analyst_result = analyze(ticker, raw_data, calc_result, score_result)

    # Assemble final output
    result = {
        "ticker": ticker,
        "analyzed_at": datetime.utcnow().isoformat(),
        "company": raw_data.get("company", {}),
        "price": raw_data.get("price", {}),
        "score": {
            "total_score": score_result.get("total_score"),
            "rating": score_result.get("rating"),
            "confidence": score_result.get("confidence"),
            "breakdown": score_result.get("breakdown", {}),
        },
        "valuation": {
            "dcf": calc_result.get("dcf", {}),
            "multiples": calc_result.get("multiples", {}),
        },
        "quality": calc_result.get("quality", {}),
        "technical": calc_result.get("technical", {}),
        "risk": calc_result.get("risk", {}),
        "growth": calc_result.get("growth", {}),
        "perspectives": analyst_result.get("perspectives", {}),
        "composite_stars": analyst_result.get("composite_stars"),
        "synthesis": analyst_result.get("synthesis", {}),
        "analyst_consensus": raw_data.get("analyst", {}),
        "news": raw_data.get("news", [])[:5],
    }

    # Step 5: Save to DB (TrackRecord)
    if save and user_id:
        decision_id = _save_to_db(ticker, result, user_id)
        result["decision_id"] = decision_id

    return result
