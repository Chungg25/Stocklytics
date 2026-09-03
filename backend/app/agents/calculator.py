"""
CalculatorAgent — CODE ONLY
Nhận raw data từ DataCollector, chạy công thức tài chính bằng Python.
Không dùng AI. Cùng input → cùng output.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import numpy as np
from typing import Optional


def _d(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _pct(val) -> Optional[float]:
    if val is None:
        return None
    return round(float(val) * 100, 2)


def _calc_dcf(fcf: float, growth_rate: float, discount_rate: float,
              terminal_growth: float, shares: float, years: int = 10) -> dict:
    if not all([fcf, shares]) or fcf <= 0 or shares <= 0:
        return {"error": "Insufficient data for DCF"}

    g = min(growth_rate or 0.05, 0.30)
    r = max(discount_rate or 0.10, 0.06)
    tg = min(terminal_growth or 0.03, r - 0.02)

    projected_fcfs = []
    current_fcf = fcf
    for yr in range(1, years + 1):
        effective_g = g * (1 - (yr - 1) / (years * 2))
        current_fcf *= (1 + effective_g)
        projected_fcfs.append(current_fcf)

    pv_fcfs = sum(cf / (1 + r) ** i for i, cf in enumerate(projected_fcfs, 1))

    terminal_value = projected_fcfs[-1] * (1 + tg) / (r - tg)
    pv_terminal = terminal_value / (1 + r) ** years

    enterprise_value = pv_fcfs + pv_terminal
    fair_value_per_share = round(float(enterprise_value / shares), 2)

    return {
        "fair_value": fair_value_per_share,
        "enterprise_value": round(float(enterprise_value), 0),
        "pv_fcfs": round(float(pv_fcfs), 0),
        "pv_terminal": round(float(pv_terminal), 0),
        "wacc": round(r, 4),
        "growth_rate": round(g, 4),
        "terminal_growth": round(tg, 4),
        "years": years,
    }


def _calc_wacc(market_cap: float, total_debt: float, cost_of_equity: float = 0.10,
               cost_of_debt: float = 0.05, tax_rate: float = 0.21) -> float:
    if not market_cap:
        return 0.10
    total = market_cap + (total_debt or 0)
    if total <= 0:
        return 0.10
    e_weight = market_cap / total
    d_weight = (total_debt or 0) / total
    return e_weight * cost_of_equity + d_weight * cost_of_debt * (1 - tax_rate)


def _calc_piotroski(data: dict) -> dict:
    f = data.get("fundamentals", {})
    score = 0
    details = {}

    # 1. Net Income > 0
    eps = f.get("eps_trailing")
    details["net_income_positive"] = bool(eps and eps > 0)
    if details["net_income_positive"]:
        score += 1

    # 2. ROA > 0
    roa = f.get("roa")
    details["roa_positive"] = bool(roa and roa > 0)
    if details["roa_positive"]:
        score += 1

    # 3. Operating Cash Flow > 0
    ocf = f.get("operating_cash_flow")
    details["ocf_positive"] = bool(ocf and ocf > 0)
    if details["ocf_positive"]:
        score += 1

    # 4. Cash Flow > Net Income (quality of earnings)
    fcf = f.get("free_cash_flow")
    revenue = f.get("revenue_ttm")
    if ocf and revenue and revenue > 0:
        ocf_margin = ocf / revenue
        profit_margin = f.get("profit_margin") or 0
        details["cash_flow_quality"] = ocf_margin > profit_margin
    else:
        details["cash_flow_quality"] = False
    if details["cash_flow_quality"]:
        score += 1

    # 5. Debt/Equity declining (assume positive if < 100)
    de = f.get("debt_to_equity")
    details["low_leverage"] = bool(de is not None and de < 100)
    if details["low_leverage"]:
        score += 1

    # 6. Current Ratio > 1
    cr = f.get("current_ratio")
    details["current_ratio_ok"] = bool(cr and cr > 1)
    if details["current_ratio_ok"]:
        score += 1

    # 7. No dilution (shares not increasing significantly — assume pass if data available)
    details["no_dilution"] = True
    score += 1

    # 8. Gross Margin improving (assume check gross_margin > 20%)
    gm = f.get("gross_margin")
    details["gross_margin_healthy"] = bool(gm and gm > 0.20)
    if details["gross_margin_healthy"]:
        score += 1

    # 9. Asset Turnover (revenue / total assets — approximate via ROA / profit margin)
    details["asset_efficiency"] = bool(roa and roa > 0.05)
    if details["asset_efficiency"]:
        score += 1

    return {"score": score, "max": 9, "details": details}


def _calc_altman_z(data: dict) -> Optional[dict]:
    f = data.get("fundamentals", {})
    p = data.get("price", {})

    market_cap = p.get("market_cap")
    total_debt = f.get("total_debt")
    revenue = f.get("revenue_ttm")
    total_cash = f.get("total_cash")

    if not all([market_cap, revenue]):
        return None

    total_assets_est = (total_debt or 0) + (market_cap or 0) * 0.6
    if total_assets_est <= 0:
        return None

    working_capital = (total_cash or 0) - (total_debt or 0) * 0.3
    retained_earnings = revenue * (f.get("profit_margin") or 0.05) * 3
    ebit = revenue * (f.get("operating_margin") or 0.10)

    a = working_capital / total_assets_est
    b = retained_earnings / total_assets_est
    c = ebit / total_assets_est
    d = market_cap / max(total_debt or 1, 1)
    e = revenue / total_assets_est

    z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

    if z > 2.99:
        zone = "Safe"
    elif z > 1.81:
        zone = "Grey"
    else:
        zone = "Distress"

    return {"z_score": round(z, 2), "zone": zone, "components": {
        "A_working_capital": round(a, 4),
        "B_retained_earnings": round(b, 4),
        "C_ebit": round(c, 4),
        "D_market_equity": round(d, 4),
        "E_asset_turnover": round(e, 4),
    }}


def _calc_technical(history: list) -> dict:
    if len(history) < 50:
        return {"error": "Not enough history for technical analysis"}

    closes = np.array([h["close"] for h in history], dtype=float)

    # SMA
    sma20 = round(float(np.mean(closes[-20:])), 2) if len(closes) >= 20 else None
    sma50 = round(float(np.mean(closes[-50:])), 2) if len(closes) >= 50 else None
    sma200 = round(float(np.mean(closes[-200:])), 2) if len(closes) >= 200 else None

    # RSI (14-period)
    deltas = np.diff(closes[-15:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0.0001
    rs = avg_gain / max(avg_loss, 0.0001)
    rsi = round(100 - (100 / (1 + rs)), 2)

    # MACD (12, 26, 9)
    macd_signal = "neutral"
    macd_value = None
    if len(closes) >= 26:
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        macd_line = ema12 - ema26
        macd_value = round(float(macd_line), 4)
        if len(closes) >= 35:
            macd_series = np.array([_ema(closes[:i+1], 12) - _ema(closes[:i+1], 26)
                                    for i in range(25, len(closes))])
            signal_line = _ema(macd_series, 9)
            macd_signal = "bullish" if macd_line > signal_line else "bearish"

    # Volatility (annualized)
    returns = np.diff(closes[-61:]) / closes[-61:-1] if len(closes) >= 61 else np.array([])
    volatility = round(float(np.std(returns) * np.sqrt(252)), 4) if len(returns) > 10 else None

    # Sharpe (simplified, risk-free rate = 4.5%)
    sharpe = None
    if volatility and volatility > 0 and len(returns) > 10:
        annualized_return = float(np.mean(returns) * 252)
        sharpe = round((annualized_return - 0.045) / volatility, 2)

    # Support / Resistance
    support, resistance = _calc_sr_levels(closes)

    current = float(closes[-1])

    return {
        "rsi": rsi,
        "rsi_signal": "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral",
        "macd": macd_value,
        "macd_signal": macd_signal,
        "sma20": sma20,
        "sma50": sma50,
        "sma200": sma200,
        "trend": _determine_trend(current, sma50, sma200),
        "volatility": volatility,
        "sharpe": sharpe,
        "support": support,
        "resistance": resistance,
    }


def _ema(data, period):
    if len(data) < period:
        return float(np.mean(data))
    multiplier = 2 / (period + 1)
    ema = float(np.mean(data[:period]))
    for val in data[period:]:
        ema = (float(val) - ema) * multiplier + ema
    return ema


def _determine_trend(price, sma50, sma200):
    if sma50 is None or sma200 is None:
        return "unknown"
    if price > sma50 > sma200:
        return "strong_uptrend"
    if price > sma50:
        return "uptrend"
    if price < sma50 < sma200:
        return "strong_downtrend"
    if price < sma50:
        return "downtrend"
    return "sideways"


def _calc_sr_levels(closes):
    from scipy.signal import argrelextrema
    order = max(5, len(closes) // 20)
    current = float(closes[-1])

    local_max = argrelextrema(closes, np.greater_equal, order=order)[0]
    local_min = argrelextrema(closes, np.less_equal, order=order)[0]

    resistance = sorted(set(round(float(closes[i]), 2) for i in local_max))
    support = sorted(set(round(float(closes[i]), 2) for i in local_min))

    resistance = [r for r in resistance if r > current][:3]
    support = [s for s in support if s < current][-3:]

    return support, resistance


def _calc_growth(data: dict) -> dict:
    f = data.get("fundamentals", {})
    rev_growth = f.get("revenue_growth")
    earn_growth = f.get("earnings_growth")

    eps_t = f.get("eps_trailing")
    eps_f = f.get("eps_forward")
    eps_growth_implied = None
    if eps_t and eps_f and eps_t > 0:
        eps_growth_implied = round((eps_f - eps_t) / abs(eps_t), 4)

    return {
        "revenue_growth_yoy": rev_growth,
        "earnings_growth_yoy": earn_growth,
        "eps_growth_implied": eps_growth_implied,
    }


def calculate(data: dict) -> dict:
    """
    Nhận output của DataCollector, trả về tất cả phép tính.
    """
    if "error" in data:
        return data

    f = data.get("fundamentals", {})
    p = data.get("price", {})

    # --- DCF ---
    fcf = f.get("free_cash_flow") or 0
    shares = f.get("shares_outstanding") or 0
    market_cap = p.get("market_cap") or 0
    total_debt = f.get("total_debt") or 0

    wacc = _calc_wacc(market_cap, total_debt)
    growth = f.get("revenue_growth") or 0.05
    dcf = _calc_dcf(fcf, growth, wacc, 0.03, shares)

    # --- Multiples ---
    multiples = {
        "pe_trailing": f.get("pe_trailing"),
        "pe_forward": f.get("pe_forward"),
        "ev_ebitda": f.get("ev_to_ebitda"),
        "ev_revenue": f.get("ev_to_revenue"),
        "price_to_book": f.get("price_to_book"),
        "price_to_sales": f.get("price_to_sales"),
        "peg_ratio": f.get("peg_ratio"),
    }

    # --- Quality ---
    piotroski = _calc_piotroski(data)
    altman = _calc_altman_z(data)

    # --- Technical ---
    technical = _calc_technical(data.get("history_1y", []))

    # --- Growth ---
    growth_metrics = _calc_growth(data)

    # --- Risk ---
    beta = p.get("beta")
    risk = {
        "beta": beta,
        "volatility": technical.get("volatility") if isinstance(technical, dict) else None,
        "sharpe": technical.get("sharpe") if isinstance(technical, dict) else None,
        "debt_to_equity": f.get("debt_to_equity"),
        "current_ratio": f.get("current_ratio"),
    }

    return {
        "ticker": data.get("ticker"),
        "dcf": dcf,
        "multiples": multiples,
        "quality": {
            "piotroski": piotroski,
            "altman_z": altman,
        },
        "technical": technical,
        "growth": growth_metrics,
        "risk": risk,
    }
