from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.stock_service import get_top_stocks, get_benchmark_data

app = FastAPI(title="Stocklytics API")

# Configure CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Stocklytics API"}

@app.get("/api/stocks")
def get_stocks():
    # Gọi hàm fetch dữ liệu thực từ yfinance
    stocks = get_top_stocks()
    return stocks

from pydantic import BaseModel

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    prompt: str

@app.post("/api/backtest")
def run_strategy_backtest(req: BacktestRequest):
    try:
        from app.services.backtest_service import run_backtest
        result = run_backtest(req.ticker, req.start_date, req.end_date, req.prompt)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
