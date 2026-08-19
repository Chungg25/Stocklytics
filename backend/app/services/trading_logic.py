import time
import math
import re
from datetime import datetime, timezone
import yfinance as yf

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from app.repositories.supabase_repo import db_repo
from app.services.ai_service import generate_ai_assessment
from app.services.search_service import get_latest_news, get_technical_indicators, get_fundamental_data
from app.ai.parsers import parse_trading_decision

def is_us_market_open():
    """Kiem tra xem thi truong My co dang mo cua khong (9:30 AM - 4:00 PM EST, Thu 2 - Thu 6)"""
    try:
        ny_time = datetime.now(ZoneInfo("America/New_York"))
        if ny_time.weekday() > 4:
            return False
            
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= ny_time <= market_close
    except Exception as e:
        print(f"[Trading] Loi kiem tra gio mo cua: {e}")
        return True # Fallback

def execute_paper_trade(ticker: str, decision: str, decision_id: str = None, tp: float = None, sl: float = None):
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.fast_info.last_price
        
        if not current_price:
            print(f"Khong the lay gia cho {ticker}")
            return
        
        portfolios = db_repo.get_portfolios()
        if not portfolios:
            print("Chua co Portfolio nao trong DB, bo qua khop lenh.")
            return
            
        portfolio_id = portfolios[0]['id']
        cash_balance = portfolios[0]['cash_balance']
        
        current_pos = db_repo.get_position(portfolio_id, ticker)
        
        if decision == "BUY":
            allocated_cash = cash_balance * 0.10
            quantity = math.floor(allocated_cash / current_price)
            total_value = current_price * quantity
            
            if quantity <= 0:
                print(f"[Trading] Khong du tien mua toi thieu 1 CP {ticker}")
                return
                
            print(f"[Trading] MUA {quantity} {ticker} @ ${current_price:.2f} (Tong: ${total_value:.2f})")
            
            if cash_balance >= total_value:
                db_repo.update_cash_balance(portfolio_id, cash_balance - total_value)
                
                if current_pos:
                    new_qty = current_pos['quantity'] + quantity
                    new_avg = ((current_pos['quantity'] * current_pos['average_entry_price']) + total_value) / new_qty
                    db_repo.update_position(current_pos['id'], {
                        "quantity": new_qty, 
                        "average_entry_price": new_avg,
                        "take_profit": tp or current_pos.get('take_profit'),
                        "stop_loss": sl or current_pos.get('stop_loss')
                    })
                else:
                    db_repo.insert_position({
                        "portfolio_id": portfolio_id,
                        "ticker": ticker,
                        "quantity": quantity,
                        "average_entry_price": current_price,
                        "take_profit": tp,
                        "stop_loss": sl
                    })
                    
                db_repo.insert_trade({
                    "portfolio_id": portfolio_id,
                    "decision_id": decision_id,
                    "ticker": ticker,
                    "trade_type": "BUY",
                    "quantity": quantity,
                    "execution_price": current_price,
                    "total_value": total_value
                })
                print(f"[Trading] Hoan tat MUA {ticker}")
            
        elif decision == "SELL" and current_pos:
            sell_qty = current_pos['quantity']
            actual_total_value = current_price * sell_qty
            
            print(f"[Trading] BAN {sell_qty} {ticker} @ ${current_price:.2f} (Tong: ${actual_total_value:.2f})")
            
            db_repo.update_cash_balance(portfolio_id, cash_balance + actual_total_value)
            db_repo.delete_position(current_pos['id'])
            
            db_repo.insert_trade({
                "portfolio_id": portfolio_id,
                "decision_id": decision_id,
                "ticker": ticker,
                "trade_type": "SELL",
                "quantity": sell_qty,
                "execution_price": current_price,
                "total_value": actual_total_value
            })
            print(f"[Trading] Hoan tat BAN {ticker}")
            
    except Exception as e:
        print(f"[Trading] Loi khop lenh: {e}")

def monitor_open_positions():
    try:
        positions = db_repo.get_all_positions()
        if not positions: return
        
        for pos in positions:
            ticker = pos['ticker']
            tp = pos.get('take_profit')
            sl = pos.get('stop_loss')
            
            if not tp and not sl: continue
            
            try:
                stock = yf.Ticker(ticker)
                current_price = stock.fast_info.last_price
            except:
                continue
                
            if current_price is None: continue
            
            if sl and current_price <= sl:
                print(f"[Auto TP/SL] {ticker} cham STOP LOSS ({current_price} <= {sl}). Ban thao!")
                execute_paper_trade(ticker, "SELL", None)
            elif tp and current_price >= tp:
                print(f"[Auto TP/SL] {ticker} cham TAKE PROFIT ({current_price} >= {tp}). Chot loi!")
                execute_paper_trade(ticker, "SELL", None)
                
    except Exception as e:
        print(f"[Auto TP/SL] Loi khi quet gia: {e}")

def run_agent_for_ticker(ticker: str, context: str = None, last_analysis_str: str = None):
    try:
        now = datetime.now(timezone.utc)
        
        needs_full = True
        if last_analysis_str and context:
            try:
                last_dt = datetime.fromisoformat(last_analysis_str.replace('Z', '+00:00'))
                if (now - last_dt).total_seconds() < 86400: # 24 hours
                    needs_full = False
            except Exception as e:
                print(f"[Trading] Parse datetime error: {e}")
                
        print(f"[Trading] Thu thap data cho {ticker}...")
        ta_data = get_technical_indicators(ticker)
        latest_news = get_latest_news(ticker, max_results=3)
        fundamental_data = get_fundamental_data(ticker)
        
        enhanced_context = f"{context}\n\n[FUNDAMENTAL_DATA]\n{fundamental_data}\n\n[TECHNICAL_INDICATORS]\n{ta_data}\n\n[LATEST_NEWS]\n{latest_news}"

        mode = "tradingagents" if needs_full else "tradingagents_fast"
        print(f"[Trading] Kich hoat {mode.upper()} cho {ticker}...")
        
        generator = generate_ai_assessment(ticker, mode=mode, context=enhanced_context)
            
        full_text = ""
        for chunk in generator:
            full_text += chunk
            print(".", end="", flush=True)
        print() 
            
        if needs_full:
            match = re.search(r'(### 3\..*?)(?=### 7\.)', full_text, re.DOTALL)
            if match:
                extracted_context = match.group(1).strip()
                db_repo.update_watchlist(ticker, {
                    "fundamental_context": extracted_context,
                    "last_full_analysis": now.isoformat()
                })
                print(f"[Trading] Da luu Context cho {ticker}")
            
        parsed = parse_trading_decision(full_text)
        decision = parsed["decision"]
        take_profit = parsed["take_profit"]
        stop_loss = parsed["stop_loss"]
            
        print(f"[Trading] {ticker} Decision: {decision} | TP: {take_profit} | SL: {stop_loss}")
        
        # Luu quyet dinh vao Database
        decision_res = db_repo.insert_ai_decision({
            "ticker": ticker,
            "decision": decision,
            "target_price": take_profit,
            "stop_loss": stop_loss,
            "rationale": full_text
        })
        
        decision_id = decision_res[0]['id'] if decision_res else None
        
        if decision in ["BUY", "SELL"]:
            execute_paper_trade(ticker, decision, decision_id, take_profit, stop_loss)
                
    except Exception as e:
        print(f"[Trading] Loi khi chay Agent cho {ticker}: {e}")

def run_all_agents():
    if not is_us_market_open():
        print("[Trading] Thi truong My DONG CUA. Tam dung quet.")
        return
        
    print("[Trading] Thi truong MO CUA. Dang tai Watchlist...")
    try:
        watchlist_items = db_repo.get_watchlist()
        if not watchlist_items:
            print("[Trading] Watchlist trong, bo qua.")
            return
            
        print(f"[Trading] Bat dau quet {len(watchlist_items)} ma...")
        for item in watchlist_items:
            run_agent_for_ticker(item["ticker"], item.get("fundamental_context"), item.get("last_full_analysis"))
            time.sleep(5)
    except Exception as e:
        print(f"[Trading] Loi khi keo Watchlist: {e}")
