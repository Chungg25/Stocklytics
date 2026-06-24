import yfinance as yf
import pandas as pd
import concurrent.futures
import math

def clean_float(val):
    if pd.isna(val) or val is None:
        return None
    return float(val)

def calculate_sentiment(hist):
    if len(hist) < 20:
        return "Neutral"

    recent_price_change = (
        hist["Close"].iloc[-1] - hist["Close"].iloc[-20]
    ) / hist["Close"].iloc[-20] * 100

    recent_volume = hist["Volume"].tail(20).mean()
    avg_volume = hist["Volume"].mean()

    if recent_price_change > 5 and recent_volume > avg_volume:
        return "Bullish"
    elif recent_price_change < -5 and recent_volume > avg_volume:
        return "Bearish"

    return "Neutral"

def format_market_cap(value):
    if not value or pd.isna(value):
        return "N/A"
    if value >= 1e12:
        return f"{value/1e12:.2f}T"
    if value >= 1e9:
        return f"{value/1e9:.2f}B"
    if value >= 1e6:
        return f"{value/1e6:.2f}M"
    return f"{value:,.0f}"

def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        hist_1y = ticker.history(period="1y")

        if hist_1y.empty:
            return None

        current_price = clean_float(hist_1y["Close"].iloc[-1])
        prev_close = clean_float(info.get("previousClose"))

        change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0

        market_cap_raw = info.get("marketCap", 0)
        market_cap = format_market_cap(market_cap_raw)

        start_price = clean_float(hist_1y["Close"].iloc[0])
        roi_1y = ((current_price - start_price) / start_price) * 100 if start_price else 0.0

        sentiment = calculate_sentiment(hist_1y)
        
        # Calculate a mock score based on ROI and Sentiment
        score = 50
        if sentiment == "Bullish": score += 15
        elif sentiment == "Bearish": score -= 15
        if roi_1y and roi_1y > 20: score += 10
        elif roi_1y and roi_1y < 0: score -= 10
        score = max(0, min(100, score)) # clamp 0-100

        # Mock forecast
        forecastAmt = current_price * 1.15 if current_price else 0.0
        forecastPct = 15.0

        # Last 30 days history for sparkline
        history_30d_raw = hist_1y["Close"].tail(30).tolist()
        history_30d = [clean_float(x) for x in history_30d_raw]

        return {
            "id": ticker_symbol,
            "ticker": ticker_symbol,
            "name": info.get("shortName", ticker_symbol),
            "sector": info.get("sector", "Unknown"),
            "price": current_price or 0.0,
            "change": clean_float(change_pct) or 0.0,
            "forecastAmt": forecastAmt,
            "forecastPct": forecastPct,
            "marketCap": market_cap,
            "score": score,
            "sentiment": sentiment,
            "roi1y": clean_float(roi_1y) or 0.0,
            "history": history_30d
        }
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}")
        return None

def get_top_stocks():
    tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "LLY", "AVGO", "TSLA",
        "JPM", "UNH", "V", "XOM", "MA", "JNJ", "PG", "HD", "COST", "ABBV",
        "MRK", "CRM", "BAC", "CVX", "NFLX", "KO", "PEP", "WMT", "TMO", "AMD",
        "MCD", "DIS", "CSCO", "ABNB", "INTU", "QCOM", "AMAT", "IBM", "TXN", "NOW",
        "GE", "CAT", "UBER", "INTC", "PFE", "NKE", "BA", "HON", "SBUX", "VZ"
    ]
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(get_stock_data, t): t for t in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)

    results.sort(key=lambda x: x['id'])
    
    return results

def get_benchmark_data(sector_name=""):
    try:
        category_map = {
            "top25": ["NVDA", "MSFT", "AAPL", "AMZN", "META"],
            "technology": ["AAPL", "MSFT", "NVDA", "AVGO", "CSCO"],
            "healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
            "financial": ["JPM", "V", "MA", "BAC", "WFC"],
            "consumer": ["AMZN", "HD", "MCD", "NKE", "SBUX"],
            "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
            "communication": ["GOOGL", "META", "NFLX", "DIS", "VZ"]
        }
        top_tickers = category_map.get(sector_name, ["AAPL", "MSFT", "GOOGL"])
        
        tickers_str = "^GSPC " + " ".join(top_tickers)
        data = yf.Tickers(tickers_str)
        hist = data.history(start="2021-01-01", interval="1mo")
        
        if hist.empty:
            return []

        try:
            sp500_close = hist["Close"]["^GSPC"]
            stock_closes = {t: hist["Close"][t] for t in top_tickers if t in hist["Close"]}
        except KeyError:
            return []

        sp500_start = clean_float(sp500_close.dropna().iloc[0]) if not sp500_close.dropna().empty else None
        
        stock_starts = {}
        for t, close_series in stock_closes.items():
            start_val = clean_float(close_series.dropna().iloc[0]) if not close_series.dropna().empty else None
            if start_val:
                stock_starts[t] = start_val
        
        chart_data = []
        
        for date in hist.index:
            s_price = clean_float(sp500_close.get(date))
            if not sp500_start or s_price is None:
                continue
                
            sp500_pct = ((s_price - sp500_start) / sp500_start) * 100
            
            sector_pcts = []
            for t, close_series in stock_closes.items():
                if t in stock_starts:
                    t_price = clean_float(close_series.get(date))
                    if t_price is not None and not pd.isna(t_price):
                        pct = ((t_price - stock_starts[t]) / stock_starts[t]) * 100
                        sector_pcts.append(pct)
            
            if sector_pcts:
                sector_avg_pct = sum(sector_pcts) / len(sector_pcts)
                chart_data.append({
                    "date": date.strftime("%Y-%m"),
                    "sp500": round(sp500_pct, 2),
                    "sector": round(sector_avg_pct, 2)
                })
        return chart_data
    except Exception as e:
        print(f"Error fetching benchmark: {e}")
        return []
