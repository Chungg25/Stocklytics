"""
PeerComparisonAgent — UC2: So sánh cổ phiếu
Chạy DataCollector + Calculator + Scoring cho mỗi mã (parallel),
xếp hạng, phát hiện anomaly, rồi AI viết báo cáo so sánh.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from app.agents.data_collector import collect
from app.agents.calculator import calculate
from app.agents.scoring import score


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


def _rank_by_metric(results: list, metric_path: str, higher_is_better: bool = True) -> list:
    """Rank tickers by a nested metric value."""
    items = []
    for r in results:
        val = r
        for key in metric_path.split("."):
            val = val.get(key, {}) if isinstance(val, dict) else None
            if val is None:
                break
        items.append({"ticker": r["ticker"], "value": val})

    valid = [i for i in items if i["value"] is not None]
    invalid = [i for i in items if i["value"] is None]

    valid.sort(key=lambda x: x["value"], reverse=higher_is_better)

    ranked = []
    for rank, item in enumerate(valid, 1):
        ranked.append({**item, "rank": rank})
    for item in invalid:
        ranked.append({**item, "rank": len(valid) + 1})

    return ranked


def _detect_anomalies(results: list) -> list:
    """Detect interesting discrepancies between peers."""
    anomalies = []

    for r in results:
        t = r["ticker"]
        calc = r.get("calc_result", {})
        raw = r.get("raw_data", {})
        f = raw.get("fundamentals", {})
        m = calc.get("multiples", {})

        rev_growth = f.get("revenue_growth")
        pe = m.get("pe_trailing")
        dcf = calc.get("dcf", {})
        price = raw.get("price", {}).get("current", 0)
        fair_value = dcf.get("fair_value")

        if rev_growth and pe:
            if rev_growth > 0.20 and pe and pe < 25:
                anomalies.append(
                    f"{t}: growth +{round(rev_growth*100)}% nhưng P/E chỉ {round(pe)}x → potential undervalued"
                )
            if rev_growth < 0.10 and pe and pe > 80:
                anomalies.append(
                    f"{t}: P/E {round(pe)}x nhưng growth chỉ +{round(rev_growth*100)}% → overvalued risk"
                )

        if fair_value and price and price > 0:
            upside = (fair_value - price) / price
            if upside > 0.30:
                anomalies.append(
                    f"{t}: DCF fair value ${round(fair_value)} vs price ${round(price)} → upside +{round(upside*100)}%"
                )
            elif upside < -0.25:
                anomalies.append(
                    f"{t}: DCF fair value ${round(fair_value)} vs price ${round(price)} → overvalued {round(upside*100)}%"
                )

        tech = calc.get("technical", {})
        rsi = tech.get("rsi")
        if rsi and rsi < 30:
            anomalies.append(f"{t}: RSI {round(rsi)} → oversold territory")
        elif rsi and rsi > 70:
            anomalies.append(f"{t}: RSI {round(rsi)} → overbought territory")

    return anomalies


def _build_rankings(results: list) -> dict:
    """Build per-metric and overall rankings."""
    metrics = {
        "pe": ("calc_result.multiples.pe_trailing", False),
        "rev_growth": ("raw_data.fundamentals.revenue_growth", True),
        "dcf_upside": (None, True),
        "piotroski": ("calc_result.quality.piotroski.score", True),
        "profit_margin": ("raw_data.fundamentals.profit_margin", True),
        "roe": ("raw_data.fundamentals.roe", True),
    }

    by_metric = {}
    for name, (path, higher) in metrics.items():
        if path:
            by_metric[name] = _rank_by_metric(results, path, higher)

    # DCF upside: computed
    dcf_items = []
    for r in results:
        price = r.get("raw_data", {}).get("price", {}).get("current", 0)
        fair = r.get("calc_result", {}).get("dcf", {}).get("fair_value")
        if fair and price and price > 0:
            upside = round((fair - price) / price * 100, 1)
        else:
            upside = None
        dcf_items.append({"ticker": r["ticker"], "value": upside})

    valid_dcf = [i for i in dcf_items if i["value"] is not None]
    invalid_dcf = [i for i in dcf_items if i["value"] is None]
    valid_dcf.sort(key=lambda x: x["value"], reverse=True)
    by_metric["dcf_upside"] = [
        {**item, "rank": rank} for rank, item in enumerate(valid_dcf, 1)
    ] + [{**item, "rank": len(valid_dcf) + 1} for item in invalid_dcf]

    # Overall by score
    overall = sorted(
        [{"ticker": r["ticker"], "score": r["score_result"].get("total_score", 0)}
         for r in results],
        key=lambda x: x["score"], reverse=True
    )
    for rank, item in enumerate(overall, 1):
        item["rank"] = rank

    return {"overall": overall, "by_metric": by_metric}


def _format_value(key: str, val) -> str:
    if val is None:
        return "N/A"
    if key in ("rev_growth", "profit_margin", "roe"):
        return f"+{round(val*100)}%" if val > 0 else f"{round(val*100)}%"
    if key == "pe":
        return f"{round(val)}x"
    if key == "dcf_upside":
        return f"+{val}%" if val > 0 else f"{val}%"
    if key == "piotroski":
        return f"{val}/9"
    return str(val)


def _ai_synthesize(tickers: list, rankings: dict, anomalies: list,
                   results: list) -> dict:
    """LLM call: synthesize comparison into verdict."""
    from app.ai.llm_client import execute_with_fallback
    import json
    import re

    rankings_text = "OVERALL RANKING:\n"
    for item in rankings["overall"]:
        rankings_text += f"  #{item['rank']} {item['ticker']} — Score: {item['score']}/100\n"

    rankings_text += "\nBY METRIC:\n"
    for metric, ranked in rankings["by_metric"].items():
        rankings_text += f"  {metric}: "
        rankings_text += ", ".join(
            f"#{r['rank']} {r['ticker']} ({_format_value(metric, r['value'])})"
            for r in ranked
        )
        rankings_text += "\n"

    anomalies_text = "\n".join(f"- {a}" for a in anomalies) if anomalies else "None detected"

    company_info = ""
    for r in results:
        c = r.get("raw_data", {}).get("company", {})
        p = r.get("raw_data", {}).get("price", {})
        company_info += f"\n{r['ticker']}: {c.get('name', '')} | ${p.get('current', 'N/A')} | Sector: {c.get('sector', '')} | Industry: {c.get('industry', '')}"

    try:
        response = execute_with_fallback(
            messages=[
                {"role": "system", "content": """You are a stock comparison analyst. You receive pre-calculated rankings and anomalies. Your job is to:
1. Pick the "best for" each purpose (growth, value, risk/reward) with a one-sentence reason
2. Declare an overall winner
3. Write a concise 2-3 sentence summary highlighting the key tension between these stocks

Respond ONLY in valid JSON:
{
  "best_for": {
    "growth": {"ticker": "X", "reason": "..."},
    "value": {"ticker": "X", "reason": "..."},
    "risk_reward": {"ticker": "X", "reason": "..."}
  },
  "winner": {"ticker": "X", "score": <number>},
  "summary": "<2-3 sentences>"
}"""},
                {"role": "user", "content": f"""Compare these stocks:
{company_info}

{rankings_text}

ANOMALIES:
{anomalies_text}
"""}
            ],
            response_format={"type": "json_object"},
            stream=False
        )
        clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return json.loads(clean)
    except Exception as e:
        winner = rankings["overall"][0] if rankings["overall"] else {"ticker": tickers[0], "score": 0}
        return {
            "best_for": {},
            "winner": winner,
            "summary": f"Comparison synthesis unavailable: {str(e)}",
            "error": str(e),
        }


def compare(tickers: list[str]) -> dict:
    """
    UC2 entry point. So sánh danh sách tickers.
    """
    tickers = [t.upper().strip() for t in tickers]
    if len(tickers) < 2:
        return {"error": "Cần ít nhất 2 mã để so sánh"}
    if len(tickers) > 5:
        tickers = tickers[:5]

    # Parallel data collection + calculation + scoring
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(len(tickers), 5)) as executor:
        futures = {executor.submit(_analyze_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result()
                if "error" in result:
                    errors.append({"ticker": ticker, "error": result["error"]})
                else:
                    results.append(result)
            except Exception as e:
                errors.append({"ticker": ticker, "error": str(e)})

    if len(results) < 2:
        return {"error": "Không đủ dữ liệu để so sánh", "errors": errors}

    # Build rankings (code — deterministic)
    rankings = _build_rankings(results)

    # Detect anomalies (code — deterministic)
    anomalies = _detect_anomalies(results)

    # Build comparison table data
    comparison_table = {}
    for r in results:
        t = r["ticker"]
        s = r["score_result"]
        c = r["calc_result"]
        raw = r["raw_data"]
        f = raw.get("fundamentals", {})
        p = raw.get("price", {})
        dcf = c.get("dcf", {})
        price = p.get("current", 0)
        fair = dcf.get("fair_value")

        comparison_table[t] = {
            "company": raw.get("company", {}).get("name", t),
            "price": price,
            "score": s.get("total_score"),
            "rating": s.get("rating"),
            "pe_trailing": c.get("multiples", {}).get("pe_trailing"),
            "rev_growth": f.get("revenue_growth"),
            "profit_margin": f.get("profit_margin"),
            "roe": f.get("roe"),
            "dcf_fair_value": fair,
            "dcf_upside_pct": round((fair - price) / price * 100, 1) if fair and price else None,
            "piotroski": c.get("quality", {}).get("piotroski", {}).get("score"),
            "altman_z": c.get("quality", {}).get("altman_z", {}).get("z_score") if c.get("quality", {}).get("altman_z") else None,
            "rsi": c.get("technical", {}).get("rsi"),
            "trend": c.get("technical", {}).get("trend"),
            "beta": p.get("beta"),
        }

    # Sector from first result
    sector = results[0].get("raw_data", {}).get("company", {}).get("sector", "")

    # AI synthesis (LLM)
    ai_verdict = _ai_synthesize(tickers, rankings, anomalies, results)

    return {
        "type": "comparison",
        "tickers": [r["ticker"] for r in results],
        "sector": sector,
        "comparison_table": comparison_table,
        "rankings": rankings,
        "anomalies": anomalies,
        "best_for": ai_verdict.get("best_for", {}),
        "winner": ai_verdict.get("winner", {}),
        "summary": ai_verdict.get("summary", ""),
        "errors": errors if errors else None,
    }
