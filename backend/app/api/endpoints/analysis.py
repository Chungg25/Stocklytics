"""
Analysis API — UC1 (single stock) + UC2 (comparison) endpoints.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AnalyzeRequest(BaseModel):
    ticker: str


class QuickScoreRequest(BaseModel):
    ticker: str


class CompareRequest(BaseModel):
    tickers: list[str]
    auto_peers: bool = False


class SuggestRequest(BaseModel):
    screen: str = "quality_growth"
    theme: Optional[str] = None
    max_picks: int = 8


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


@router.post("/suggest")
def run_suggestion(req: SuggestRequest):
    try:
        from app.agents.suggester import suggest

        if req.max_picks < 1 or req.max_picks > 15:
            raise HTTPException(status_code=400, detail="max_picks phải từ 1-15")

        result = suggest(
            screen=req.screen,
            theme=req.theme,
            max_picks=req.max_picks,
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
def run_comparison(req: CompareRequest):
    try:
        from app.agents.comparator import compare

        if len(req.tickers) < 1:
            raise HTTPException(status_code=400, detail="At least 1 ticker is required")
        if not req.auto_peers and len(req.tickers) < 2:
            raise HTTPException(status_code=400, detail="At least 2 tickers are required for comparison, or enable auto_peers")
        if len(req.tickers) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 tickers allowed")

        result = compare(req.tickers, auto_peers=req.auto_peers)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
