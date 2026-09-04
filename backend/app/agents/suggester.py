"""
IdeaGenerationAgent — UC3: Stock Suggestion / Screening
Scans the ~130-stock universe with screening presets, scores and ranks,
then uses LLM to produce actionable picks with entry/SL/TP and diversification analysis.
"""

import math
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from app.agents.data_collector import collect
from app.agents.calculator import calculate
from app.agents.scoring import score


SCREENING_PRESETS = {
    "quality_growth": {
        "label": "Quality Growth",
        "description": "High-quality compounders: strong fundamentals + double-digit growth",
        "filters": {
            "pe_max": None,
            "pe_below_sector_median": True,
            "fcf_yield_min": 0.05,
            "roe_min": 0.15,
            "rev_growth_min": 0.15,
            "piotroski_min": 6,
            "rsi_min": 30,
            "rsi_max": 70,
        },
    },
    "value": {
        "label": "Deep Value",
        "description": "Undervalued stocks with margin of safety from DCF + multiples",
        "filters": {
            "pe_max": 20,
            "dcf_upside_min": 0.20,
            "piotroski_min": 5,
            "altman_z_min": 1.8,
            "rsi_max": 65,
        },
    },
    "growth": {
        "label": "High Growth",
        "description": "Fastest growers with revenue acceleration and momentum",
        "filters": {
            "rev_growth_min": 0.20,
            "profit_margin_positive": True,
            "rsi_min": 40,
            "trend_bullish": True,
        },
    },
    "momentum": {
        "label": "Momentum",
        "description": "Technically strong stocks riding uptrends with volume confirmation",
        "filters": {
            "trend_bullish": True,
            "rsi_min": 50,
            "rsi_max": 75,
            "sma_above_200": True,
            "score_min": 55,
        },
    },
    "dividend_safety": {
        "label": "Safe Dividend",
        "description": "Financially sound dividend payers with low risk",
        "filters": {
            "dividend_yield_min": 0.015,
            "piotroski_min": 6,
            "altman_z_min": 2.0,
            "beta_max": 1.2,
        },
    },
}

STOCK_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "CSCO", "CRM",
    "ADBE", "NFLX", "INTC", "AMD", "TXN", "QCOM", "INTU", "IBM", "AMAT", "NOW",
    "UBER", "ABNB", "ORCL", "PANW", "SNPS", "CDNS", "KLAC", "MU", "LRCX", "ADI",
    "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C", "BLK",
    "SPGI", "BX", "PGR", "CB", "MMC", "CME", "SCHW", "AON", "ICE", "MCO",
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "DHR", "ISRG", "SYK",
    "MDT", "VRTX", "REGN", "ELV", "BSX", "ZTS", "CI", "GILD", "CVS", "BDX",
    "WMT", "PG", "HD", "COST", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT",
    "LOW", "TJX", "MO", "PM", "EL", "CL", "KMB", "GIS", "SYY", "DG",
    "BRK-B", "XOM", "CVX", "GE", "CAT", "BA", "HON", "VZ", "T", "NEE",
    "COP", "SLB", "EOG", "PXD", "MPC", "PSX", "VLO", "OXY", "HES", "HAL",
    "RTX", "UNP", "UPS", "LMT", "DE", "WM", "GD", "NSC", "NOC", "CSX",
]

SECTOR_MAP = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "CSCO", "CRM",
                   "ADBE", "NFLX", "INTC", "AMD", "TXN", "QCOM", "INTU", "IBM", "AMAT", "NOW",
                   "UBER", "ABNB", "ORCL", "PANW", "SNPS", "CDNS", "KLAC", "MU", "LRCX", "ADI"],
    "Financials": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C", "BLK",
                   "SPGI", "BX", "PGR", "CB", "MMC", "CME", "SCHW", "AON", "ICE", "MCO"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "DHR", "ISRG", "SYK",
                   "MDT", "VRTX", "REGN", "ELV", "BSX", "ZTS", "CI", "GILD", "CVS", "BDX"],
    "Consumer": ["WMT", "PG", "HD", "COST", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT",
                 "LOW", "TJX", "MO", "PM", "EL", "CL", "KMB", "GIS", "SYY", "DG"],
    "Industrials & Energy": ["BRK-B", "XOM", "CVX", "GE", "CAT", "BA", "HON", "VZ", "T", "NEE",
                             "COP", "SLB", "EOG", "PXD", "MPC", "PSX", "VLO", "OXY", "HES", "HAL",
                             "RTX", "UNP", "UPS", "LMT", "DE", "WM", "GD", "NSC", "NOC", "CSX"],
}

THEME_KEYWORDS = {
    "ai": ["NVDA", "MSFT", "GOOGL", "META", "AMD", "AVGO", "ORCL", "NOW", "CRM", "PANW", "SNPS", "CDNS", "AMAT", "KLAC", "LRCX", "MU", "ADI"],
    "cloud": ["MSFT", "AMZN", "GOOGL", "CRM", "NOW", "ORCL", "PANW", "SNPS"],
    "cybersecurity": ["PANW", "CRWD", "ZS", "FTNT", "CSCO"],
    "ev": ["TSLA", "RIVN", "NIO", "LI", "GM", "F"],
    "healthcare_innovation": ["LLY", "ISRG", "DHR", "TMO", "VRTX", "REGN", "BSX", "SYK"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "MPC", "PSX", "VLO", "OXY", "HES", "HAL"],
    "dividend": ["JNJ", "KO", "PEP", "PG", "MO", "PM", "VZ", "T", "XOM", "CVX", "MCD", "HD"],
    "fintech": ["V", "MA", "AXP", "SQ", "PYPL", "BLK", "SPGI", "ICE", "CME"],
}


def _clean_nan(obj):
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


def _analyze_one(ticker: str) -> dict:
    raw_data = collect(ticker)
    if "error" in raw_data:
        return {"ticker": ticker, "error": raw_data["error"]}

    calc_result = calculate(raw_data)
    if "error" in calc_result:
        return {"ticker": ticker, "error": calc_result["error"]}

    score_result = score(calc_result, raw_data)

    return {
        "ticker": ticker,
        "raw_data": raw_data,
        "calc_result": calc_result,
        "score_result": score_result,
    }


def _get_metric(result: dict, path: str, default=None):
    val = result
    for key in path.split("."):
        if isinstance(val, dict):
            val = val.get(key)
        else:
            return default
        if val is None:
            return default
    return val


def _passes_filters(result: dict, filters: dict, sector_pe_median: float = None) -> bool:
    raw = result["raw_data"]
    calc = result["calc_result"]
    sc = result["score_result"]
    f = raw.get("fundamentals", {})
    p = raw.get("price", {})
    tech = calc.get("technical", {})
    quality = calc.get("quality", {})
    dcf = calc.get("dcf", {})
    price = p.get("current", 0)
    pe = calc.get("multiples", {}).get("pe_trailing")

    if "pe_max" in filters and filters["pe_max"] is not None:
        if pe is None or pe <= 0 or pe > filters["pe_max"]:
            return False

    if filters.get("pe_below_sector_median") and sector_pe_median:
        if pe is None or pe <= 0 or pe > sector_pe_median:
            return False

    if "fcf_yield_min" in filters:
        fcf_yield = f.get("free_cash_flow_yield") or f.get("fcf_yield")
        if fcf_yield is None:
            mcap = p.get("market_cap", 0)
            fcf = f.get("free_cash_flow", 0)
            fcf_yield = fcf / mcap if mcap and mcap > 0 else 0
        if fcf_yield < filters["fcf_yield_min"]:
            return False

    if "roe_min" in filters:
        roe = f.get("roe")
        if roe is None or roe < filters["roe_min"]:
            return False

    if "rev_growth_min" in filters:
        rg = f.get("revenue_growth")
        if rg is None or rg < filters["rev_growth_min"]:
            return False

    if "piotroski_min" in filters:
        pio = quality.get("piotroski", {}).get("score")
        if pio is None or pio < filters["piotroski_min"]:
            return False

    if "altman_z_min" in filters:
        az = quality.get("altman_z", {})
        z = az.get("z_score") if az else None
        if z is None or z < filters["altman_z_min"]:
            return False

    rsi = tech.get("rsi")
    if "rsi_min" in filters:
        if rsi is None or rsi < filters["rsi_min"]:
            return False
    if "rsi_max" in filters:
        if rsi is None or rsi > filters["rsi_max"]:
            return False

    if filters.get("trend_bullish"):
        trend = tech.get("trend", "")
        if trend not in ("bullish", "strong_bullish"):
            return False

    if filters.get("sma_above_200"):
        sma200 = tech.get("sma_200")
        if not sma200 or not price or price < sma200:
            return False

    if "score_min" in filters:
        total = sc.get("total_score", 0)
        if total < filters["score_min"]:
            return False

    if "dcf_upside_min" in filters:
        fair = dcf.get("fair_value")
        if not fair or not price or price <= 0:
            return False
        upside = (fair - price) / price
        if upside < filters["dcf_upside_min"]:
            return False

    if filters.get("profit_margin_positive"):
        pm = f.get("profit_margin")
        if pm is None or pm <= 0:
            return False

    if "dividend_yield_min" in filters:
        dy = f.get("dividend_yield") or p.get("dividend_yield", 0)
        if dy is None or dy < filters["dividend_yield_min"]:
            return False

    if "beta_max" in filters:
        beta = p.get("beta")
        if beta is None or beta > filters["beta_max"]:
            return False

    return True


def _calc_correlation_matrix(results: list) -> dict:
    tickers = []
    return_series = []

    for r in results:
        history = r.get("raw_data", {}).get("history_1y", [])
        if len(history) < 50:
            continue
        closes = np.array([h["close"] for h in history], dtype=float)
        returns = np.diff(closes) / closes[:-1]
        tickers.append(r["ticker"])
        return_series.append(returns)

    if len(tickers) < 2:
        return {}

    min_len = min(len(s) for s in return_series)
    aligned = np.array([s[-min_len:] for s in return_series])
    corr = np.corrcoef(aligned)

    matrix = {}
    for i, t1 in enumerate(tickers):
        matrix[t1] = {}
        for j, t2 in enumerate(tickers):
            matrix[t1][t2] = round(float(corr[i][j]), 3)
    return matrix


def _build_sector_distribution(results: list) -> dict:
    dist = {}
    for r in results:
        sector = r.get("raw_data", {}).get("company", {}).get("sector", "Other")
        if not sector:
            sector = "Other"
        dist[sector] = dist.get(sector, 0) + 1
    return dist


def _calc_diversification_score(correlation: dict, sector_dist: dict) -> dict:
    if not correlation:
        return {"score": 50, "level": "unknown", "detail": "Insufficient data for correlation analysis"}

    tickers = list(correlation.keys())
    if len(tickers) < 2:
        return {"score": 50, "level": "unknown", "detail": "Need at least 2 stocks"}

    pair_corrs = []
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i < j:
                pair_corrs.append(correlation[t1].get(t2, 0))

    avg_corr = float(np.mean(pair_corrs)) if pair_corrs else 0
    max_corr = float(np.max(pair_corrs)) if pair_corrs else 0

    num_sectors = len(sector_dist)
    total_stocks = sum(sector_dist.values())
    concentration = max(sector_dist.values()) / total_stocks if total_stocks > 0 else 1

    corr_score = max(0, min(100, int((1 - avg_corr) * 60)))
    sector_score = min(40, num_sectors * 10)
    concentration_penalty = int(max(0, (concentration - 0.5) * 40))

    total = max(0, min(100, corr_score + sector_score - concentration_penalty))

    if total >= 70:
        level = "high"
    elif total >= 40:
        level = "moderate"
    else:
        level = "low"

    return {
        "score": total,
        "level": level,
        "avg_correlation": round(avg_corr, 3),
        "max_correlation": round(max_corr, 3),
        "num_sectors": num_sectors,
        "concentration_pct": round(concentration * 100, 1),
        "detail": f"Avg correlation {round(avg_corr, 2)}, {num_sectors} sectors, "
                  f"max sector concentration {round(concentration*100)}%"
    }


def _ai_synthesize(picks: list, screen_name: str, theme: str = None,
                   correlation: dict = None, sector_dist: dict = None,
                   diversification: dict = None) -> dict:
    from app.ai.llm_client import execute_with_fallback
    import json
    import re

    picks_text = ""
    for r in picks:
        raw = r["raw_data"]
        calc = r["calc_result"]
        sc = r["score_result"]
        f = raw.get("fundamentals", {})
        p = raw.get("price", {})
        tech = calc.get("technical", {})
        dcf = calc.get("dcf", {})
        price = p.get("current", 0)
        fair = dcf.get("fair_value")

        picks_text += f"\n\n--- {r['ticker']} ({raw.get('company', {}).get('name', '')}) ---"
        picks_text += f"\nSector: {raw.get('company', {}).get('sector', 'N/A')} | Industry: {raw.get('company', {}).get('industry', 'N/A')}"
        picks_text += f"\nPrice: ${price} | AI Score: {sc.get('total_score', 'N/A')}/100 | Rating: {sc.get('rating', 'N/A')}"
        picks_text += f"\nP/E: {calc.get('multiples', {}).get('pe_trailing', 'N/A')} | Rev Growth: {round((f.get('revenue_growth') or 0)*100, 1)}%"
        picks_text += f"\nROE: {round((f.get('roe') or 0)*100, 1)}% | Profit Margin: {round((f.get('profit_margin') or 0)*100, 1)}%"
        picks_text += f"\nPiotroski: {calc.get('quality', {}).get('piotroski', {}).get('score', 'N/A')}/9"
        az = calc.get("quality", {}).get("altman_z")
        picks_text += f" | Altman Z: {round(az.get('z_score', 0), 2) if az else 'N/A'}"
        picks_text += f"\nDCF Fair Value: ${round(fair) if fair else 'N/A'}"
        if fair and price and price > 0:
            picks_text += f" | DCF Upside: {round((fair-price)/price*100, 1)}%"
        picks_text += f"\nRSI: {round(tech.get('rsi', 0), 1)} | Trend: {tech.get('trend', 'N/A')} | Beta: {p.get('beta', 'N/A')}"

        support = tech.get("support")
        resistance = tech.get("resistance")
        if support:
            picks_text += f"\nSupport levels: {', '.join(f'${s}' for s in support[:3])}"
        if resistance:
            picks_text += f"\nResistance levels: {', '.join(f'${r}' for r in resistance[:3])}"

        scenarios = dcf.get("scenarios", {})
        if scenarios:
            picks_text += f"\nDCF Scenarios: Bear ${scenarios.get('conservative', {}).get('fair_value', 'N/A')}"
            picks_text += f" | Base ${scenarios.get('base', {}).get('fair_value', 'N/A')}"
            picks_text += f" | Bull ${scenarios.get('optimistic', {}).get('fair_value', 'N/A')}"

    corr_text = ""
    if correlation:
        corr_text = "\n\nCORRELATION BETWEEN PICKS:\n"
        tks = list(correlation.keys())
        for t1 in tks:
            pairs = ", ".join(f"{t2}={correlation[t1].get(t2, 'N/A')}" for t2 in tks if t2 != t1)
            if pairs:
                corr_text += f"  {t1}: {pairs}\n"

    sector_text = ""
    if sector_dist:
        sector_text = "\nSECTOR DISTRIBUTION: " + ", ".join(f"{s}: {c}" for s, c in sector_dist.items())

    div_text = ""
    if diversification:
        div_text = f"\nDIVERSIFICATION SCORE: {diversification.get('score', 'N/A')}/100 ({diversification.get('level', 'N/A')})"
        div_text += f"\n  {diversification.get('detail', '')}"

    ticker_list_str = ", ".join(r["ticker"] for r in picks)
    theme_instruction = ""
    if theme:
        theme_instruction = f"\nTHEME CONTEXT: The user is interested in '{theme}' stocks. Provide theme_insight explaining why these picks align with this theme and which are pure-play vs. diversified exposure."

    try:
        response = execute_with_fallback(
            messages=[
                {"role": "system", "content": f"""You are a senior equity research analyst writing actionable stock recommendations in English. Your audience is retail investors who need SPECIFIC data to make decisions — not generic commentary.

LANGUAGE: All output MUST be in English. No exceptions.

CRITICAL RULES FOR EVERY TEXT FIELD:
- NEVER write generic phrases like "strong fundamentals", "well-positioned", "attractive valuation", or "solid growth"
- ALWAYS cite the EXACT number from the data: "$142 P/E 28x vs sector median 35x", "ROE 45% ranks #1 among 6 screened stocks"
- ALWAYS compare: vs sector median, vs peers in this screen, vs historical range
- Every sentence must contain at least one specific number or data point

SUMMARY RULES:
- Start with screening result: "Screened X stocks with [preset name] filters, Y passed"
- Name the #1 pick and WHY with 2-3 key metrics
- End with the key risk/opportunity trade-off across all picks using specific numbers
- Example: "Screened 130 stocks with Quality Growth filters, 6 passed. NVDA leads with 82/100 score driven by 122% revenue growth and 18.5% DCF upside, though its 1.65 beta signals higher volatility than the group average of 1.1."

THESIS RULES (per pick):
- Sentence 1: The core value proposition with P/E, growth rate, and DCF upside vs current price
- Sentence 2: Quality confirmation citing Piotroski score, ROE ranking, or margin trend
- Sentence 3: Technical timing — RSI level, trend direction, proximity to support/resistance
- BAD: "NVDA is well-positioned in the AI space with strong growth"
- GOOD: "NVDA trades at 45x P/E with 122% revenue growth, implying a PEG of 0.37 — cheapest among AI-exposed picks. Piotroski 7/9 and 55% net margin confirm operational quality. RSI at 55 in bullish trend with $125 support suggests favorable entry timing."

CATALYST RULES:
- Must be a SPECIFIC upcoming event or data point, not a trend
- BAD: "AI demand growth" / GOOD: "Next earnings report expected to show >100% data center revenue growth based on current booking trends"

TOP_RISK RULES:
- Must quantify the downside: "P/E compression to sector median 35x implies 22% downside to $105"
- Never generic: avoid "market volatility" or "competition"

ENTRY/STOP-LOSS/TARGET PRICE RULES:
- entry_price: current price or nearest support level for a better entry
- stop_loss: below the strongest support level (typically 5-10% below entry). State which support level it references
- target_price: the more conservative of nearest resistance and DCF base-case fair value
- All must be specific dollar amounts

PORTFOLIO ALLOCATION RULES:
- Percentages must sum to 100
- allocation_rationale must explain WHY the weights differ using risk/reward ratios, conviction levels, and correlation between picks
- BAD: "Higher allocation to stronger picks" / GOOD: "NVDA gets 30% as highest-conviction BUY with 25% expected return and 82/100 score; AVGO gets 25% for lower beta (1.2 vs NVDA's 1.65) at similar DCF upside; remaining split equally for diversification given 0.72 NVDA-AVGO correlation"

DIVERSIFICATION INSIGHT RULES:
- Must reference the correlation matrix: name the highest-correlated pair and their coefficient
- Must reference sector concentration percentage
- Must suggest what sector/stock to ADD if diversification is low
- BAD: "The portfolio is moderately diversified" / GOOD: "4 of 6 picks are Technology (67% concentration) with NVDA-AVGO correlation at 0.72. Adding a Healthcare pick like LLY (0.25 correlation with NVDA) or a Consumer Staple like PG would reduce portfolio beta from 1.4 to ~1.1"

Respond ONLY in valid JSON:
{{
  "summary": "<string per rules above>",
  "picks": [
    {{
      "ticker": "<TICKER>",
      "action": "BUY|ACCUMULATE|WATCH",
      "conviction": "high|medium|low",
      "thesis": "<3 sentences per rules above>",
      "catalyst": "<1 sentence per rules above>",
      "top_risk": "<1 sentence with quantified downside>",
      "entry_price": <number>,
      "stop_loss": <number>,
      "target_price": <number>,
      "expected_return_pct": <number>,
      "key_metrics": {{
        "score": <number>,
        "pe": <number or null>,
        "rev_growth_pct": <number>,
        "roe_pct": <number>,
        "dcf_upside_pct": <number or null>,
        "piotroski": <number or null>
      }}
    }}
  ],
  "portfolio_allocation": {{
    "<TICKER>": <percent as integer>
  }},
  "allocation_rationale": "<per rules above>",
  "diversification_insight": "<per rules above>",
  "theme_insight": "<1-2 sentences about theme alignment with specific numbers, or null if no theme>"
}}

All tickers to include: {ticker_list_str}
Screen used: {screen_name}
Number of stocks that passed screen: {len(picks)} out of universe{theme_instruction}"""},
                {"role": "user", "content": f"""Generate investment recommendations for these screened stocks:
{picks_text}
{sector_text}{div_text}{corr_text}"""}
            ],
            response_format={"type": "json_object"},
            stream=False
        )
        clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return json.loads(clean)
    except Exception as e:
        return {
            "summary": f"AI synthesis unavailable: {str(e)}",
            "picks": [],
            "portfolio_allocation": {},
            "allocation_rationale": "",
            "diversification_insight": "",
            "theme_insight": None,
            "error": str(e),
        }


def suggest(
    screen: str = "quality_growth",
    theme: str = None,
    max_picks: int = 8,
    custom_filters: dict = None,
) -> dict:
    """
    UC3 entry point. Screen the stock universe and return actionable picks.

    Args:
        screen: Preset name from SCREENING_PRESETS or "custom"
        theme: Optional thematic filter (e.g. "ai", "energy", "dividend")
        max_picks: Maximum number of picks to return (default 8)
        custom_filters: Custom filter dict (used when screen="custom")
    """
    started_at = datetime.utcnow()

    preset = SCREENING_PRESETS.get(screen)
    if not preset and screen != "custom":
        screen = "quality_growth"
        preset = SCREENING_PRESETS["quality_growth"]

    if screen == "custom" and custom_filters:
        filters = custom_filters
        screen_label = "Custom Screen"
    elif preset:
        filters = preset["filters"]
        screen_label = preset["label"]
    else:
        filters = SCREENING_PRESETS["quality_growth"]["filters"]
        screen_label = "Quality Growth"

    universe = list(STOCK_UNIVERSE)
    if theme:
        theme_lower = theme.lower().replace(" ", "_")
        theme_tickers = THEME_KEYWORDS.get(theme_lower, [])
        if theme_tickers:
            theme_set = set(t.upper() for t in theme_tickers)
            universe = [t for t in universe if t in theme_set]
            if len(universe) < 3:
                universe = list(theme_set & set(STOCK_UNIVERSE))
                if len(universe) < 3:
                    universe = list(STOCK_UNIVERSE)

    universe_size = len(universe)

    all_results = []
    errors = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(_analyze_one, t): t for t in universe}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                if "error" in result:
                    errors.append({"ticker": ticker, "error": result["error"]})
                else:
                    all_results.append(result)
            except Exception as e:
                errors.append({"ticker": ticker, "error": str(e)})

    if not all_results:
        return {"error": "Could not fetch data for any stock in the universe", "errors": errors}

    all_results = _clean_nan(all_results)

    pe_values = []
    for r in all_results:
        pe = r.get("calc_result", {}).get("multiples", {}).get("pe_trailing")
        if pe and pe > 0:
            pe_values.append(pe)
    sector_pe_median = float(np.median(pe_values)) if pe_values else None

    filtered = []
    for r in all_results:
        if _passes_filters(r, filters, sector_pe_median):
            filtered.append(r)

    filtered.sort(key=lambda r: r["score_result"].get("total_score", 0), reverse=True)

    picks = filtered[:max_picks]

    if len(picks) < 2 and len(all_results) >= 2:
        all_results.sort(key=lambda r: r["score_result"].get("total_score", 0), reverse=True)
        picks = all_results[:max_picks]
        screen_label += " (relaxed — few stocks passed strict filters)"

    correlation = _calc_correlation_matrix(picks) if len(picks) >= 2 else {}
    sector_dist = _build_sector_distribution(picks)
    diversification = _calc_diversification_score(correlation, sector_dist)

    ai_result = _ai_synthesize(picks, screen_label, theme, correlation, sector_dist, diversification)

    picks_output = []
    ai_picks_map = {}
    for ap in ai_result.get("picks", []):
        ai_picks_map[ap.get("ticker", "")] = ap

    for rank, r in enumerate(picks, 1):
        t = r["ticker"]
        raw = r["raw_data"]
        calc = r["calc_result"]
        sc = r["score_result"]
        f = raw.get("fundamentals", {})
        p = raw.get("price", {})
        tech = calc.get("technical", {})
        dcf = calc.get("dcf", {})
        price = p.get("current", 0)
        fair = dcf.get("fair_value")

        ai_pick = ai_picks_map.get(t, {})

        support = tech.get("support", [])
        resistance = tech.get("resistance", [])
        entry = ai_pick.get("entry_price", price)
        sl = ai_pick.get("stop_loss")
        tp = ai_pick.get("target_price")

        if not sl and support:
            sl = round(min(support) * 0.97, 2)
        if not sl:
            sl = round(price * 0.92, 2)

        if not tp and fair:
            tp = round(fair, 2)
        elif not tp and resistance:
            tp = round(max(resistance), 2)
        if not tp:
            tp = round(price * 1.15, 2)

        expected_return = round((tp - entry) / entry * 100, 1) if entry and entry > 0 else None

        picks_output.append({
            "rank": rank,
            "ticker": t,
            "company_name": raw.get("company", {}).get("name", t),
            "sector": raw.get("company", {}).get("sector", ""),
            "industry": raw.get("company", {}).get("industry", ""),
            "price": price,
            "score": sc.get("total_score", 0),
            "rating": sc.get("rating", "N/A"),
            "action": ai_pick.get("action", "WATCH"),
            "conviction": ai_pick.get("conviction", "medium"),
            "thesis": ai_pick.get("thesis", ""),
            "catalyst": ai_pick.get("catalyst", ""),
            "top_risk": ai_pick.get("top_risk", ""),
            "entry_price": entry,
            "stop_loss": sl,
            "target_price": tp,
            "expected_return_pct": ai_pick.get("expected_return_pct", expected_return),
            "key_metrics": {
                "pe": calc.get("multiples", {}).get("pe_trailing"),
                "rev_growth_pct": round((f.get("revenue_growth") or 0) * 100, 1),
                "roe_pct": round((f.get("roe") or 0) * 100, 1),
                "profit_margin_pct": round((f.get("profit_margin") or 0) * 100, 1),
                "dcf_upside_pct": round((fair - price) / price * 100, 1) if fair and price and price > 0 else None,
                "piotroski": calc.get("quality", {}).get("piotroski", {}).get("score"),
                "rsi": tech.get("rsi"),
                "beta": p.get("beta"),
            },
        })

    result = {
        "type": "suggestion",
        "screen_used": screen,
        "screen_label": screen_label,
        "theme": theme,
        "universe_size": universe_size,
        "scanned_count": len(all_results),
        "filtered_count": len(filtered),
        "pick_count": len(picks_output),

        "summary": ai_result.get("summary", ""),
        "picks": picks_output,

        "portfolio_allocation": ai_result.get("portfolio_allocation", {}),
        "allocation_rationale": ai_result.get("allocation_rationale", ""),

        "diversification": {
            "sector_distribution": sector_dist,
            "correlation": correlation,
            "score": diversification,
            "insight": ai_result.get("diversification_insight", ""),
        },

        "theme_insight": ai_result.get("theme_insight"),

        "available_screens": {k: {"label": v["label"], "description": v["description"]}
                             for k, v in SCREENING_PRESETS.items()},
        "available_themes": list(THEME_KEYWORDS.keys()),

        "scan_errors": errors[:10] if errors else None,
        "_generated_at": started_at.isoformat(),
    }

    return _clean_nan(result)
