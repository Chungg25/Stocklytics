from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services.stock_service import get_top_stocks, get_benchmark_data
from app.services.scanner_service import run_daily_scan
from app.services.compare_service import get_compare_data

router = APIRouter()

@router.get("/stocks")
def get_stocks():
    return get_top_stocks()

@router.get("/benchmark")
def get_benchmark(sector: str = Query("top25")):
    return get_benchmark_data(sector)

@router.post("/scan-signals")
def trigger_scan():
    try:
        result = run_daily_scan()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

class CompareRequest(BaseModel):
    tickers: list[str]
    timeframe: str
    indicators: list[str]

@router.post("/compare")
def run_compare(req: CompareRequest):
    if len(req.tickers) > 50:
        return {"status": "error", "message": "Cannot compare more than 50 tickers at once."}
    try:
        data = get_compare_data(req.tickers, req.timeframe, req.indicators)
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
