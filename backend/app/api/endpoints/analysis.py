"""
UC1 Analysis API — Full stock analysis endpoint.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AnalyzeRequest(BaseModel):
    ticker: str


class QuickScoreRequest(BaseModel):
    ticker: str


@router.post("/analyze")
def run_full_analysis(req: AnalyzeRequest, x_user_id: Optional[str] = Header(None)):
    try:
        from app.agents.orchestrator import analyze_stock
        result = analyze_stock(req.ticker, user_id=x_user_id, save=bool(x_user_id))
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-score")
def run_quick_score(req: QuickScoreRequest):
    try:
        from app.agents.data_collector import collect
        from app.agents.calculator import calculate
        from app.agents.scoring import score

        raw_data = collect(req.ticker)
        if "error" in raw_data:
            raise HTTPException(status_code=404, detail=raw_data["error"])

        calc_result = calculate(raw_data)
        if "error" in calc_result:
            raise HTTPException(status_code=500, detail=calc_result["error"])

        score_result = score(calc_result, raw_data)
        return {
            "status": "success",
            "data": {
                "ticker": req.ticker.upper(),
                "total_score": score_result.get("total_score"),
                "rating": score_result.get("rating"),
                "confidence": score_result.get("confidence"),
                "breakdown": score_result.get("breakdown", {}),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
