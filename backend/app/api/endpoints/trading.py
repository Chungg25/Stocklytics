from fastapi import APIRouter
from pydantic import BaseModel
from app.services.backtest_service import run_backtest
from app.services.sheets_service import load_groups, save_groups
from app.db import supabase
import yfinance as yf

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

class TradeRequest(BaseModel):
    user_id: str
    ticker: str
    quantity: int
    trade_type: str # 'BUY' or 'SELL'

@router.post("/execute")
def execute_paper_trade(req: TradeRequest):
    try:
        # Get current price
        stock = yf.Ticker(req.ticker)
        current_price = stock.info.get('currentPrice') or stock.history(period="1d")['Close'].iloc[-1]
        current_price = float(current_price)
        
        # Get portfolio
        port_res = supabase.table('paper_portfolio').select('*').eq('user_id', req.user_id).execute()
        if not port_res.data:
            return {"status": "error", "message": "Portfolio not found. Please initialize portfolio first."}
        portfolio = port_res.data[0]
        
        total_cost = current_price * req.quantity
        
        if req.trade_type == 'BUY':
            if portfolio['cash_balance'] < total_cost:
                return {"status": "error", "message": "Insufficient cash balance"}
            new_cash = portfolio['cash_balance'] - total_cost
        elif req.trade_type == 'SELL':
            # Check if has enough positions
            pos_res = supabase.table('paper_positions').select('*').eq('portfolio_id', portfolio['id']).eq('ticker', req.ticker).execute()
            current_qty = pos_res.data[0]['quantity'] if pos_res.data else 0
            if current_qty < req.quantity:
                return {"status": "error", "message": "Insufficient shares to sell"}
            new_cash = portfolio['cash_balance'] + total_cost
        else:
            return {"status": "error", "message": "Invalid trade type"}
            
        # Update Portfolio Cash
        supabase.table('paper_portfolio').update({'cash_balance': new_cash}).eq('id', portfolio['id']).execute()
        
        # Log Trade
        supabase.table('paper_trades').insert({
            'portfolio_id': portfolio['id'],
            'ticker': req.ticker,
            'trade_type': req.trade_type,
            'quantity': req.quantity,
            'execution_price': current_price,
            'user_id': req.user_id
        }).execute()
        
        # Update Position
        pos_res = supabase.table('paper_positions').select('*').eq('portfolio_id', portfolio['id']).eq('ticker', req.ticker).execute()
        if pos_res.data:
            pos = pos_res.data[0]
            if req.trade_type == 'BUY':
                new_qty = pos['quantity'] + req.quantity
                # Calculate new average entry price
                old_total = pos['quantity'] * pos['average_entry_price']
                new_avg = (old_total + total_cost) / new_qty
                supabase.table('paper_positions').update({'quantity': new_qty, 'average_entry_price': new_avg}).eq('id', pos['id']).execute()
            else:
                new_qty = pos['quantity'] - req.quantity
                if new_qty == 0:
                    supabase.table('paper_positions').delete().eq('id', pos['id']).execute()
                else:
                    supabase.table('paper_positions').update({'quantity': new_qty}).eq('id', pos['id']).execute()
        else:
            if req.trade_type == 'BUY':
                supabase.table('paper_positions').insert({
                    'portfolio_id': portfolio['id'],
                    'ticker': req.ticker,
                    'quantity': req.quantity,
                    'average_entry_price': current_price,
                    'user_id': req.user_id
                }).execute()
                
        # Trigger Sync
        sync_portfolio(req.user_id)
        
        return {"status": "success", "message": f"Successfully {req.trade_type} {req.quantity} shares of {req.ticker}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/portfolio/sync/{user_id}")
def sync_portfolio(user_id: str):
    """Update current prices, PnL, and total equity for a user's portfolio."""
    try:
        port_res = supabase.table('paper_portfolio').select('*').eq('user_id', user_id).execute()
        if not port_res.data:
            return {"status": "error", "message": "Portfolio not found"}
        portfolio = port_res.data[0]
        
        pos_res = supabase.table('paper_positions').select('*').eq('portfolio_id', portfolio['id']).execute()
        
        total_positions_value = 0
        for pos in pos_res.data:
            try:
                stock = yf.Ticker(pos['ticker'])
                current_price = stock.info.get('currentPrice') or stock.history(period="1d")['Close'].iloc[-1]
                current_price = float(current_price)
                
                unrealized_pnl = (current_price - pos['average_entry_price']) * pos['quantity']
                total_positions_value += (current_price * pos['quantity'])
                
                supabase.table('paper_positions').update({
                    'unrealized_pnl': round(unrealized_pnl, 2)
                }).eq('id', pos['id']).execute()
            except Exception as e:
                print(f"Failed to sync {pos['ticker']}: {e}")
                # Fallback to old average value to prevent wiping out equity on error
                total_positions_value += (pos['average_entry_price'] * pos['quantity'])
                
        new_total_equity = portfolio['cash_balance'] + total_positions_value
        supabase.table('paper_portfolio').update({
            'total_equity': round(new_total_equity, 2)
        }).eq('id', portfolio['id']).execute()
        
        return {"status": "success", "message": "Portfolio synced"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

