"""
OrchestratorAgent — UC1 Entry Point
Chains: DataCollector → Calculator → Scoring → Analyst → TrackRecord
"""

from datetime import datetime
from app.agents.data_collector import collect
from app.agents.calculator import calculate
from app.agents.scoring import score
from app.agents.analyst import analyze


def _save_to_db(ticker: str, result: dict, user_id: str = None):
    try:
        from app.db import supabase
        if not supabase or not user_id:
            return None

        synthesis = result.get("synthesis", {})
        score_data = result.get("score", {})

        record = {
            "user_id": user_id,
            "ticker": ticker,
            "action": synthesis.get("decision", "Gray Zone"),
            "reasoning": synthesis.get("summary", ""),
            "ai_score": score_data.get("total_score"),
            "ai_rating": score_data.get("rating"),
            "price_at_decision": result.get("price", {}).get("current"),
        }

        resp = supabase.table("ai_decisions").insert(record).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


def _build_price_levels(raw_data: dict, calc_result: dict, actionable: dict) -> list:
    """
    Collect all significant price levels from multiple sources.
    Each level has: price, type, source, label — for drawing on TradingView chart.
    """
    levels = []
    price = raw_data.get("price", {}).get("current", 0)
    tech = calc_result.get("technical", {})
    dcf = calc_result.get("dcf", {})
    analyst = raw_data.get("analyst", {})

    if price:
        levels.append({"price": price, "type": "current", "source": "market",
                        "label": f"Current ${price}"})

    for s in tech.get("support", []):
        levels.append({"price": s, "type": "support", "source": "technical",
                        "label": f"Support ${s} (1Y local minimum)"})

    for r in tech.get("resistance", []):
        levels.append({"price": r, "type": "resistance", "source": "technical",
                        "label": f"Resistance ${r} (1Y local maximum)"})

    sma50 = tech.get("sma50")
    sma200 = tech.get("sma200")
    if sma50:
        levels.append({"price": round(sma50, 2), "type": "sma", "source": "technical",
                        "label": f"SMA50 ${round(sma50, 2)}"})
    if sma200:
        levels.append({"price": round(sma200, 2), "type": "sma", "source": "technical",
                        "label": f"SMA200 ${round(sma200, 2)}"})

    fair_value = dcf.get("fair_value")
    if fair_value:
        levels.append({"price": round(fair_value, 2), "type": "fair_value", "source": "dcf",
                        "label": f"DCF Fair Value ${round(fair_value, 2)}"})

    scenarios = dcf.get("scenarios", {})
    for scenario_name, sc_data in scenarios.items():
        sv = sc_data.get("fair_value")
        if sv:
            levels.append({"price": round(sv, 2), "type": "scenario",
                            "source": f"dcf_{scenario_name}",
                            "label": f"DCF {scenario_name.capitalize()} ${round(sv, 2)}"})

    target_mean = analyst.get("target_mean")
    target_low = analyst.get("target_low")
    target_high = analyst.get("target_high")
    if target_mean:
        levels.append({"price": round(target_mean, 2), "type": "analyst_target",
                        "source": "analyst_consensus",
                        "label": f"Analyst Target ${round(target_mean, 2)}"})
    if target_low:
        levels.append({"price": round(target_low, 2), "type": "analyst_low",
                        "source": "analyst_consensus",
                        "label": f"Analyst Low ${round(target_low, 2)}"})
    if target_high:
        levels.append({"price": round(target_high, 2), "type": "analyst_high",
                        "source": "analyst_consensus",
                        "label": f"Analyst High ${round(target_high, 2)}"})

    if actionable:
        entry = actionable.get("entry_price")
        tp = actionable.get("target_price")
        sl = actionable.get("stop_loss")
        if entry:
            levels.append({"price": entry, "type": "entry", "source": "ai_setup",
                            "label": f"Entry ${entry}",
                            "reasoning": actionable.get("entry_reasoning", "")})
        if tp:
            levels.append({"price": tp, "type": "take_profit", "source": "ai_setup",
                            "label": f"Target ${tp}",
                            "reasoning": actionable.get("target_reasoning", "")})
        if sl:
            levels.append({"price": sl, "type": "stop_loss", "source": "ai_setup",
                            "label": f"Stop Loss ${sl}",
                            "reasoning": actionable.get("stop_reasoning", "")})

    levels.sort(key=lambda x: x["price"])
    return levels


def analyze_stock(ticker: str, user_id: str = None, save: bool = True) -> dict:
    """
    UC1 full pipeline. Returns structured analysis result.
    """
    ticker = ticker.upper().strip()

    # Step 1: Collect raw data
    raw_data = collect(ticker)
    if "error" in raw_data:
        return {"error": raw_data["error"], "ticker": ticker}

    # Step 2: Calculate financial metrics
    calc_result = calculate(raw_data)
    if "error" in calc_result:
        return {"error": calc_result["error"], "ticker": ticker}

    # Step 3: Score (deterministic)
    score_result = score(calc_result, raw_data)

    # Step 4: LLM analysis (4 Masters + synthesis)
    analyst_result = analyze(ticker, raw_data, calc_result, score_result)

    # Assemble full_report_markdown
    synthesis = analyst_result.get("synthesis", {})
    actionable = synthesis.get("actionable_setup", {})

    md_report = f"## {ticker} — {synthesis.get('decision', 'N/A')}\n\n"
    md_report += f"**Thesis:** {synthesis.get('thesis', '')}\n\n"

    if actionable:
        md_report += "### Actionable Setup\n"
        md_report += f"| | Price | Reasoning |\n|---|---|---|\n"
        md_report += f"| **Entry** | ${actionable.get('entry_price', 'N/A')} | {actionable.get('entry_reasoning', '')} |\n"
        md_report += f"| **Target** | ${actionable.get('target_price', 'N/A')} | {actionable.get('target_reasoning', '')} |\n"
        md_report += f"| **Stop Loss** | ${actionable.get('stop_loss', 'N/A')} | {actionable.get('stop_reasoning', '')} |\n\n"
        md_report += f"Risk/Reward: {actionable.get('risk_reward_ratio', 'N/A')} | "
        md_report += f"Expected Return: {actionable.get('expected_return_pct', 'N/A')}% | "
        md_report += f"Max Loss: {actionable.get('max_loss_pct', 'N/A')}%\n\n"

    for key, pers in analyst_result.get("perspectives", {}).items():
        name = pers.get("name", key.capitalize())
        stars = pers.get("stars", 3)
        analysis = pers.get("analysis", "")
        if not analysis and "essence" in pers:
            analysis = pers.get("essence", "")
        md_report += f"### {name} ({stars} Stars)\n{analysis}\n\n"
    md_report += f"### Final Summary\n{synthesis.get('summary', '')}"

    # Extract verdicts
    perspectives_out = {}
    for key, pers in analyst_result.get("perspectives", {}).items():
        verdict = pers.get("analysis", "")
        if len(verdict) > 100:
            verdict = verdict[:97] + "..."
        if not verdict:
            verdict = pers.get("essence", "Analysis unavailable")

        perspectives_out[key] = {
            "stars": pers.get("stars", 3),
            "verdict": verdict,
            "full_data": pers,
        }

    # Format score_breakdown
    breakdown_raw = score_result.get("breakdown", {})

    # Format scenarios
    scenarios_raw = synthesis.get("scenarios", {})
    scenarios_out = {
        "bull": scenarios_raw.get("bull", {}).get("price", 0),
        "base": scenarios_raw.get("base", {}).get("price", 0),
        "bear": scenarios_raw.get("bear", {}).get("price", 0),
    }

    # Assemble final output
    result = {
        "ticker": ticker,
        "company_name": raw_data.get("company", {}).get("name", ticker),
        "price": raw_data.get("price", {}).get("current", 0),
        "score": score_result.get("total_score", 0),
        "rating": score_result.get("rating", "N/A"),
        "one_liner": synthesis.get("thesis", "Analysis generated by 4 Masters Framework."),

        "perspectives": perspectives_out,
        "composite_stars": analyst_result.get("composite_stars", 3),

        "score_breakdown": {
            "fundamentals": { "score": breakdown_raw.get("quality", 0), "details": "Derived from Quality and Growth." },
            "technical":    { "score": breakdown_raw.get("technical", 0), "details": "Derived from moving averages and momentum." },
            "sentiment":    { "score": breakdown_raw.get("sentiment", 0), "details": "Derived from news and analysts." },
            "value":        { "score": breakdown_raw.get("value", 0), "details": "Derived from DCF and Multiples." }
        },
        "valuation": {
            "dcf_fair_value": calc_result.get("dcf", {}).get("fair_value", 0),
            "dcf": calc_result.get("dcf", {}),
            "multiples": calc_result.get("multiples", {}),
            "multiples_valuation": calc_result.get("multiples_valuation", {}),
            "scenarios": scenarios_out,
        },

        "decision": synthesis.get("decision", "Gray Zone"),
        "action": synthesis.get("action", "Hold"),
        "bull_case": synthesis.get("bull_case", []),
        "bear_case": synthesis.get("bear_case", []),
        "catalysts": raw_data.get("company", {}).get("catalysts", []),

        "actionable_setup": actionable,
        "price_levels": _build_price_levels(raw_data, calc_result, actionable),

        "quality": calc_result.get("quality", {}),
        "technical": calc_result.get("technical", {}),
        "risk": calc_result.get("risk", {}),
        "growth": calc_result.get("growth", {}),
        "historical": calc_result.get("historical", {}),
        "analyst_consensus": raw_data.get("analyst", {}),
        "news": raw_data.get("news", [])[:5],

        "full_report_markdown": md_report,

        "_analyzed_at": datetime.utcnow().isoformat(),
        "_raw_synthesis": synthesis,
    }

    # Step 5: Save to DB (TrackRecord)
    if save and user_id:
        decision_id = _save_to_db(ticker, {"synthesis": synthesis, "score": score_result, "price": raw_data.get("price")}, user_id)
        result["decision_id"] = decision_id

    return result
