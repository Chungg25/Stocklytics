from fastapi import APIRouter
from pydantic import BaseModel
from app.services.backtest_service import run_backtest
from app.services.sheets_service import load_groups, save_groups

router = APIRouter()

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    prompt: str

@router.post("/backtest")
def run_strategy_backtest(req: BacktestRequest):
    try:
        result = run_backtest(req.ticker, req.start_date, req.end_date, req.prompt)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class SaveGroupsRequest(BaseModel):
    groups: dict[str, list[str]]

@router.get("/groups")
def get_groups():
    try:
        groups = load_groups()
        return {"status": "success", "groups": groups}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/groups")
def save_groups_endpoint(req: SaveGroupsRequest):
    try:
        save_groups(req.groups)
        return {"status": "success", "message": "Successfully saved groups to Google Sheets."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
