"""
ScoringAgent — CODE ONLY
Tính điểm tổng hợp minh bạch từ kết quả CalculatorAgent.
Công thức cố định, không AI. Cùng input → cùng output.
"""


def _clamp(val, low=0, high=100):
    return max(low, min(high, int(val)))


def _score_fundamentals(calc: dict, data: dict) -> dict:
    f = data.get("fundamentals", {})
    g = calc.get("growth", {})
    q = calc.get("quality", {})

    # Revenue Growth YoY (/25): >30%=25, >15%=20, >5%=15, >0%=10, negative=5
    rev_g = f.get("revenue_growth")
    if rev_g is None:
        rev_score = 10
    elif rev_g > 0.30:
        rev_score = 25
    elif rev_g > 0.15:
        rev_score = 20
    elif rev_g > 0.05:
        rev_score = 15
    elif rev_g > 0:
        rev_score = 10
    else:
        rev_score = 5

    # EPS Growth YoY (/25)
    eps_g = f.get("earnings_growth") or g.get("eps_growth_implied")
    if eps_g is None:
        eps_score = 10
    elif eps_g > 0.30:
        eps_score = 25
    elif eps_g > 0.15:
        eps_score = 20
    elif eps_g > 0.05:
        eps_score = 15
    elif eps_g > 0:
        eps_score = 10
    else:
        eps_score = 5

    # Profit Margin (/25): >20%=25, >10%=20, >5%=15, >0%=10, negative=5
    pm = f.get("profit_margin")
    if pm is None:
        pm_score = 10
    elif pm > 0.20:
        pm_score = 25
    elif pm > 0.10:
        pm_score = 20
    elif pm > 0.05:
        pm_score = 15
    elif pm > 0:
        pm_score = 10
    else:
        pm_score = 5

    # Piotroski F-Score (/25): 7-9=25, 5-6=20, 3-4=15, 0-2=10
    pio = q.get("piotroski", {}).get("score", 5)
    if pio >= 7:
        pio_score = 25
    elif pio >= 5:
        pio_score = 20
    elif pio >= 3:
        pio_score = 15
    else:
        pio_score = 10

    total = rev_score + eps_score + pm_score + pio_score
    return {
        "score": total,
        "max": 100,
        "details": {
            "revenue_growth": {"score": rev_score, "max": 25, "value": rev_g},
            "eps_growth": {"score": eps_score, "max": 25, "value": eps_g},
            "profit_margin": {"score": pm_score, "max": 25, "value": pm},
            "piotroski": {"score": pio_score, "max": 25, "value": pio},
        }
    }


def _score_technical(calc: dict) -> dict:
    t = calc.get("technical", {})

    # Trend SMA50 vs SMA200 (/30)
    trend = t.get("trend", "unknown")
    trend_map = {"strong_uptrend": 30, "uptrend": 24, "sideways": 15,
                 "downtrend": 8, "strong_downtrend": 3, "unknown": 15}
    trend_score = trend_map.get(trend, 15)

    # RSI position (/30): 40-60=30 (ideal), 30-40 or 60-70=20, <30 or >70=10
    rsi = t.get("rsi")
    if rsi is None:
        rsi_score = 15
    elif 40 <= rsi <= 60:
        rsi_score = 30
    elif 30 <= rsi < 40 or 60 < rsi <= 70:
        rsi_score = 20
    else:
        rsi_score = 10

    # MACD signal (/20)
    macd = t.get("macd_signal", "neutral")
    macd_score = 20 if macd == "bullish" else 10 if macd == "bearish" else 15

    # Distance from support (/20): closer = safer
    support = t.get("support", [])
    current = None
    if support:
        current_candidate = t.get("sma20")  # approximate current price
        dist_score = 15
    else:
        dist_score = 10

    total = trend_score + rsi_score + macd_score + dist_score
    return {
        "score": total,
        "max": 100,
        "details": {
            "trend": {"score": trend_score, "max": 30, "value": trend},
            "rsi": {"score": rsi_score, "max": 30, "value": rsi},
            "macd": {"score": macd_score, "max": 20, "value": macd},
            "support_proximity": {"score": dist_score, "max": 20},
        }
    }


def _score_sentiment(data: dict) -> dict:
    analyst = data.get("analyst", {})
    news = data.get("news", [])

    # Analyst consensus (/50)
    rec = (analyst.get("recommendation") or "").lower()
    rec_map = {"strong_buy": 50, "buy": 45, "outperform": 42,
               "overweight": 40, "hold": 25, "neutral": 25,
               "underperform": 15, "underweight": 12, "sell": 10, "strong_sell": 5}
    analyst_score = rec_map.get(rec, 25)

    # Analyst count boost
    count = analyst.get("analyst_count") or 0
    if count >= 20:
        analyst_score = min(50, analyst_score + 5)

    # News sentiment (/50): simple keyword-based scoring
    news_score = 25  # neutral default
    if news:
        positive_kw = ["beat", "surge", "record", "upgrade", "growth", "outperform",
                       "bullish", "raise", "strong", "exceed", "profit", "gain"]
        negative_kw = ["miss", "decline", "downgrade", "risk", "loss", "warning",
                       "bearish", "cut", "weak", "fall", "lawsuit", "investigation"]
        pos_count = 0
        neg_count = 0
        for n in news[:10]:
            text = (n.get("title", "") + " " + n.get("body", "")).lower()
            pos_count += sum(1 for kw in positive_kw if kw in text)
            neg_count += sum(1 for kw in negative_kw if kw in text)
        total_signals = pos_count + neg_count
        if total_signals > 0:
            sentiment_ratio = pos_count / total_signals
            news_score = _clamp(int(sentiment_ratio * 50), 10, 50)

    total = analyst_score + news_score
    return {
        "score": total,
        "max": 100,
        "details": {
            "analyst_consensus": {"score": analyst_score, "max": 50, "value": rec},
            "news_sentiment": {"score": news_score, "max": 50},
        }
    }


def _score_value(calc: dict, data: dict) -> dict:
    f = data.get("fundamentals", {})
    dcf = calc.get("dcf", {})
    m = calc.get("multiples", {})
    price = data.get("price", {}).get("current", 0)

    # P/E vs industry norm (/30): lower PE = better value
    pe = m.get("pe_trailing")
    if pe is None:
        pe_score = 15
    elif pe < 15:
        pe_score = 30
    elif pe < 25:
        pe_score = 25
    elif pe < 40:
        pe_score = 18
    elif pe < 60:
        pe_score = 12
    else:
        pe_score = 8

    # DCF upside (/40): (fair_value - price) / price
    fair = dcf.get("fair_value")
    if fair and price and price > 0:
        upside = (fair - price) / price
        if upside > 0.30:
            dcf_score = 40
        elif upside > 0.15:
            dcf_score = 32
        elif upside > 0.05:
            dcf_score = 25
        elif upside > -0.05:
            dcf_score = 18
        elif upside > -0.15:
            dcf_score = 12
        else:
            dcf_score = 5
        dcf_upside = round(upside * 100, 1)
    else:
        dcf_score = 15
        dcf_upside = None

    # PEG Ratio (/30): <1 = great, 1-2 = ok, >2 = expensive
    peg = m.get("peg_ratio")
    if peg is None or peg <= 0:
        peg_score = 15
    elif peg < 0.5:
        peg_score = 30
    elif peg < 1.0:
        peg_score = 25
    elif peg < 1.5:
        peg_score = 20
    elif peg < 2.0:
        peg_score = 15
    else:
        peg_score = 8

    total = pe_score + dcf_score + peg_score
    return {
        "score": total,
        "max": 100,
        "details": {
            "pe_valuation": {"score": pe_score, "max": 30, "value": pe},
            "dcf_upside": {"score": dcf_score, "max": 40, "value_pct": dcf_upside},
            "peg_ratio": {"score": peg_score, "max": 30, "value": peg},
        }
    }


def score(calc_result: dict, raw_data: dict) -> dict:
    """
    Nhận output của Calculator + raw data → trả về điểm tổng hợp.
    Weights: Fundamentals 30%, Technical 25%, Sentiment 25%, Value 20%
    """
    if "error" in calc_result:
        return calc_result

    fund = _score_fundamentals(calc_result, raw_data)
    tech = _score_technical(calc_result)
    sent = _score_sentiment(raw_data)
    val = _score_value(calc_result, raw_data)

    total = round(
        fund["score"] * 0.30 +
        tech["score"] * 0.25 +
        sent["score"] * 0.25 +
        val["score"] * 0.20
    )
    total = _clamp(total, 0, 100)

    if total >= 75:
        rating = "BUY"
    elif total >= 50:
        rating = "HOLD"
    else:
        rating = "SELL"

    if total >= 80:
        confidence = "HIGH"
    elif total >= 60:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "ticker": calc_result.get("ticker"),
        "total_score": total,
        "rating": rating,
        "confidence": confidence,
        "breakdown": {
            "fundamentals": {"weight": "30%", **fund},
            "technical": {"weight": "25%", **tech},
            "sentiment": {"weight": "25%", **sent},
            "value": {"weight": "20%", **val},
        },
    }
