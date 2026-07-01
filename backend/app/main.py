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

@app.get("/api/benchmark")
def get_benchmark(sector: str = Query("top25")):
    return get_benchmark_data(sector)

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

@app.post("/api/scan-signals")
def trigger_scan():
    try:
        from app.services.scanner_service import run_daily_scan
        result = run_daily_scan()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

class CompareRequest(BaseModel):
    tickers: list[str]
    timeframe: str
    indicators: list[str]

@app.post("/api/compare")
def run_compare(req: CompareRequest):
    try:
        from app.services.compare_service import get_compare_data
        data = get_compare_data(req.tickers, req.timeframe, req.indicators)
        return {"status": "success", "data": data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
