"""
DataCollectorAgent — CODE ONLY
Gọi yfinance + DuckDuckGo + Supabase DB một lần duy nhất, cache cho các agent khác.
"""

import yfinance as yf
from ddgs import DDGS
from datetime import datetime
from typing import Optional


def _safe_get(info: dict, key: str, default=None):
    val = info.get(key)
    if val is None:
        return default
    return val


def _fetch_news_ddg(ticker: str, company_name: str, max_results: int = 10) -> list:
    try:
        with DDGS() as ddgs:
            results = []
            for r in ddgs.news(f"{ticker} {company_name} stock", max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "source": r.get("source", ""),
                    "date": r.get("date", ""),
                    "body": r.get("body", ""),
                })
            return results
    except Exception:
        return []


def _fetch_news_db(ticker: str) -> list:
    try:
        from app.db import supabase
        if not supabase:
            return []
        resp = (
            supabase.table("stock_news")
            .select("title, url, source, summary, published_at")
            .eq("ticker", ticker.upper())
            .order("published_at", desc=True)
            .limit(15)
            .execute()
        )
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "source": r.get("source", ""),
                "date": r.get("published_at", ""),
                "body": r.get("summary", ""),
            }
            for r in (resp.data or [])
        ]
    except Exception:
        return []


def _merge_news(db_news: list, ddg_news: list, limit: int = 15) -> list:
    seen_urls = set()
    merged = []
    for item in db_news + ddg_news:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(item)
    return merged[:limit]


def _find_peers(info: dict, ticker: str) -> list:
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    if not industry:
        return []
    try:
        import yfinance as yf
        # yfinance doesn't have a direct peer lookup — use sector ETF holdings or hardcoded
        # For now, use the recommendedSymbols if available, or return empty
        peers = []
        # Try getting from yfinance's recommendations
        stock = yf.Ticker(ticker)
        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                pass  # recommendations is analyst ratings, not peers
        except Exception:
            pass
        return peers
    except Exception:
        return []


def collect(ticker: str) -> dict:
    """
    Thu thập toàn bộ dữ liệu cho 1 ticker.
    Returns dict với price, fundamentals, history, analyst, news.
    """
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        return {"error": f"Không tìm thấy dữ liệu cho {ticker}"}

    current_price = _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice", 0)
    company_name = _safe_get(info, "shortName", ticker)

    # --- Price data ---
    price_data = {
        "current": current_price,
        "previous_close": _safe_get(info, "previousClose"),
        "open": _safe_get(info, "open"),
        "high_52w": _safe_get(info, "fiftyTwoWeekHigh"),
        "low_52w": _safe_get(info, "fiftyTwoWeekLow"),
        "volume": _safe_get(info, "volume"),
        "avg_volume_10d": _safe_get(info, "averageVolume10days"),
        "avg_volume_3m": _safe_get(info, "averageVolume"),
        "market_cap": _safe_get(info, "marketCap"),
        "beta": _safe_get(info, "beta"),
    }

    # --- Fundamentals ---
    fundamentals = {
        "revenue_ttm": _safe_get(info, "totalRevenue"),
        "revenue_growth": _safe_get(info, "revenueGrowth"),
        "earnings_growth": _safe_get(info, "earningsGrowth"),
        "eps_trailing": _safe_get(info, "trailingEps"),
        "eps_forward": _safe_get(info, "forwardEps"),
        "pe_trailing": _safe_get(info, "trailingPE"),
        "pe_forward": _safe_get(info, "forwardPE"),
        "peg_ratio": _safe_get(info, "pegRatio"),
        "price_to_book": _safe_get(info, "priceToBook"),
        "price_to_sales": _safe_get(info, "priceToSalesTrailing12Months"),
        "enterprise_value": _safe_get(info, "enterpriseValue"),
        "ev_to_ebitda": _safe_get(info, "enterpriseToEbitda"),
        "ev_to_revenue": _safe_get(info, "enterpriseToRevenue"),
        "profit_margin": _safe_get(info, "profitMargins"),
        "operating_margin": _safe_get(info, "operatingMargins"),
        "gross_margin": _safe_get(info, "grossMargins"),
        "roe": _safe_get(info, "returnOnEquity"),
        "roa": _safe_get(info, "returnOnAssets"),
        "debt_to_equity": _safe_get(info, "debtToEquity"),
        "current_ratio": _safe_get(info, "currentRatio"),
        "free_cash_flow": _safe_get(info, "freeCashflow"),
        "operating_cash_flow": _safe_get(info, "operatingCashflow"),
        "total_cash": _safe_get(info, "totalCash"),
        "total_debt": _safe_get(info, "totalDebt"),
        "shares_outstanding": _safe_get(info, "sharesOutstanding"),
        "dividend_yield": _safe_get(info, "dividendYield"),
        "payout_ratio": _safe_get(info, "payoutRatio"),
        "ebitda": _safe_get(info, "ebitda"),
        "interest_expense": None,
        "effective_tax_rate": None,
    }

    # Fetch interest expense and tax rate from income statement
    try:
        inc = stock.income_stmt
        if inc is not None and not inc.empty:
            latest = inc.iloc[:, 0]
            if "Interest Expense" in latest.index:
                val = latest["Interest Expense"]
                if val is not None:
                    fundamentals["interest_expense"] = abs(float(val))
            pretax = latest.get("Pretax Income")
            tax = latest.get("Tax Provision")
            if pretax and tax and pretax > 0:
                fundamentals["effective_tax_rate"] = round(float(tax) / float(pretax), 4)
    except Exception:
        pass

    # --- Historical data (1y daily for technical, 5y quarterly for growth) ---
    hist_1y = stock.history(period="1y")
    close_1y = []
    if not hist_1y.empty:
        close_1y = [
            {"date": d.strftime("%Y-%m-%d"), "close": round(float(c), 2)}
            for d, c in zip(hist_1y.index, hist_1y["Close"])
        ]

    # --- Quarterly financials for growth trends ---
    quarterly_rev = []
    quarterly_eps = []
    try:
        q_fin = stock.quarterly_financials
        if q_fin is not None and not q_fin.empty:
            if "Total Revenue" in q_fin.index:
                for col in q_fin.columns[:8]:
                    val = q_fin.loc["Total Revenue", col]
                    if val is not None:
                        quarterly_rev.append({
                            "quarter": col.strftime("%Y-Q%q") if hasattr(col, 'strftime') else str(col),
                            "revenue": float(val)
                        })
    except Exception:
        pass
    try:
        q_earn = stock.quarterly_earnings
        if q_earn is not None and not q_earn.empty:
            for _, row in q_earn.iterrows():
                quarterly_eps.append({
                    "quarter": str(row.name) if hasattr(row, 'name') else "",
                    "eps": float(row.get("Earnings", 0)),
                })
    except Exception:
        pass

    # --- Analyst consensus ---
    analyst = {
        "target_mean": _safe_get(info, "targetMeanPrice"),
        "target_high": _safe_get(info, "targetHighPrice"),
        "target_low": _safe_get(info, "targetLowPrice"),
        "target_median": _safe_get(info, "targetMedianPrice"),
        "recommendation": _safe_get(info, "recommendationKey"),
        "analyst_count": _safe_get(info, "numberOfAnalystOpinions"),
    }

    # --- Company info ---
    company_info = {
        "name": company_name,
        "sector": _safe_get(info, "sector"),
        "industry": _safe_get(info, "industry"),
        "description": _safe_get(info, "longBusinessSummary", "")[:500],
        "country": _safe_get(info, "country"),
        "employees": _safe_get(info, "fullTimeEmployees"),
        "website": _safe_get(info, "website"),
    }

    # --- News (merge DB + DuckDuckGo) ---
    db_news = _fetch_news_db(ticker)
    ddg_news = _fetch_news_ddg(ticker, company_name)
    news = _merge_news(db_news, ddg_news)

    return {
        "ticker": ticker,
        "collected_at": datetime.utcnow().isoformat(),
        "company": company_info,
        "price": price_data,
        "fundamentals": fundamentals,
        "history_1y": close_1y,
        "quarterly_revenue": quarterly_rev,
        "quarterly_eps": quarterly_eps,
        "analyst": analyst,
        "news": news,
    }
