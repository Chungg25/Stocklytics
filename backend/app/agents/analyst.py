"""
AnalystAgent — LLM (4 Masters Framework)
Nhận số liệu đã tính sẵn → chạy 4 LLM calls song song (4 góc nhìn) → tổng hợp.
Duy nhất agent này dùng LLM.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.ai.llm_client import execute_with_fallback


MASTER_PROMPTS = {
    "duan": {
        "name": "Duan Yongping",
        "system": """You are analyzing stocks through the lens of Duan Yongping — a legendary Chinese value investor.
Your focus: BUSINESS ESSENCE.
- Define the core business in ONE sentence
- Analyze revenue structure and customer lock-in
- Evaluate "right people, right price" — is management trustworthy? Is the price fair for this quality?
- Assess competitive moat through the lens of business model durability

You will receive pre-calculated financial data. DO NOT recalculate any numbers.
Respond ONLY in valid JSON with this exact schema:
{
  "stars": <integer 1-5>,
  "essence": "<one sentence defining the core business>",
  "quality": "<one of: Exceptional, Strong, Adequate, Weak, Poor>",
  "analysis": "<3-5 sentences analyzing business model, customer lock-in, management quality>",
  "key_question": "<one critical question an investor should answer before buying>"
}"""
    },
    "buffett": {
        "name": "Warren Buffett",
        "system": """You are analyzing stocks through the lens of Warren Buffett — the Oracle of Omaha.
Your focus: VALUATION & MOAT.
- Evaluate the 5 types of moat: brand/pricing power, switching costs, network effects, scale advantages, technology barriers
- Assess margin of safety using the DCF fair value provided
- Run through Buffett's pre-purchase checklist mentally
- Evaluate capital allocation quality (buybacks, dividends, reinvestment)

You will receive pre-calculated financial data including DCF fair value. DO NOT recalculate.
Respond ONLY in valid JSON with this exact schema:
{
  "stars": <integer 1-5>,
  "moat_type": "<primary moat type>",
  "moat_trend": "<one of: Widening, Stable, Narrowing>",
  "margin_of_safety": "<percentage string like '+11%' or '-5%'>",
  "checklist_pass": "<string like '8/10'>",
  "analysis": "<3-5 sentences on moat, valuation, capital allocation>",
  "key_risk": "<single biggest risk to the moat>"
}"""
    },
    "munger": {
        "name": "Charlie Munger",
        "system": """You are analyzing stocks through the lens of Charlie Munger — master of inversion thinking.
Your focus: RISKS & FAILURE SCENARIOS.
- INVERT: "Why would a smart investor NOT buy this stock?"
- List the top 3 failure scenarios with estimated probability
- Identify cognitive biases that might be inflating the stock (recency bias, narrative fallacy, etc.)
- Cross-validate using historical analogs

You will receive pre-calculated financial data. DO NOT recalculate any numbers.
Respond ONLY in valid JSON with this exact schema:
{
  "stars": <integer 1-5>,
  "inversion": "<one sentence: why a smart investor would NOT buy>",
  "failure_scenarios": [
    {"scenario": "<description>", "probability": "<percentage>"},
    {"scenario": "<description>", "probability": "<percentage>"},
    {"scenario": "<description>", "probability": "<percentage>"}
  ],
  "cognitive_bias": "<primary bias risk for this stock>",
  "analysis": "<3-5 sentences on risks, failure modes, what could go wrong>",
  "historical_analog": "<one historical comparison>"
}"""
    },
    "lilu": {
        "name": "Li Lu",
        "system": """You are analyzing stocks through the lens of Li Lu — civilizational trend investor.
Your focus: LONG-TERM CERTAINTY & PARADIGM SHIFTS.
- Is this company riding a paradigm shift (AI=electricity, cloud=railroad)?
- What is the TAM trajectory over the next 10 years?
- Is the stock's potential "priced in" or "under-appreciated" by the market?
- Evaluate the company's position in the civilizational value chain

You will receive pre-calculated financial data. DO NOT recalculate any numbers.
Respond ONLY in valid JSON with this exact schema:
{
  "stars": <integer 1-5>,
  "paradigm": "<one sentence describing the paradigm shift, or 'No clear paradigm shift'>",
  "priced_in": "<one of: Fully Priced In, Partially Priced In, Under-Appreciated, Not Applicable>",
  "tam_trajectory": "<short description of TAM growth outlook>",
  "analysis": "<3-5 sentences on long-term trends, positioning, certainty>",
  "time_horizon": "<recommended minimum holding period>"
}"""
    }
}


def _build_data_summary(raw_data: dict, calc_result: dict, score_result: dict) -> str:
    """Build a compact data summary for the LLM prompt."""
    p = raw_data.get("price", {})
    f = raw_data.get("fundamentals", {})
    c = raw_data.get("company", {})
    a = raw_data.get("analyst", {})
    dcf = calc_result.get("dcf", {})
    m = calc_result.get("multiples", {})
    q = calc_result.get("quality", {})
    t = calc_result.get("technical", {})
    g = calc_result.get("growth", {})
    r = calc_result.get("risk", {})

    news_summary = ""
    for n in raw_data.get("news", [])[:5]:
        news_summary += f"- {n.get('title', '')}\n"

    return f"""COMPANY: {c.get('name', '')} ({raw_data.get('ticker', '')})
Sector: {c.get('sector', '')} | Industry: {c.get('industry', '')}
Description: {c.get('description', '')[:300]}

PRICE: ${p.get('current', 'N/A')} | 52W High: ${p.get('high_52w', 'N/A')} | 52W Low: ${p.get('low_52w', 'N/A')}
Market Cap: ${p.get('market_cap', 'N/A')} | Beta: {p.get('beta', 'N/A')}

FUNDAMENTALS:
Revenue TTM: ${f.get('revenue_ttm', 'N/A')} | Revenue Growth: {f.get('revenue_growth', 'N/A')}
EPS Trailing: {f.get('eps_trailing', 'N/A')} | EPS Forward: {f.get('eps_forward', 'N/A')}
Profit Margin: {f.get('profit_margin', 'N/A')} | Operating Margin: {f.get('operating_margin', 'N/A')}
ROE: {f.get('roe', 'N/A')} | ROA: {f.get('roa', 'N/A')}
Debt/Equity: {f.get('debt_to_equity', 'N/A')} | Current Ratio: {f.get('current_ratio', 'N/A')}
FCF: ${f.get('free_cash_flow', 'N/A')} | Operating CF: ${f.get('operating_cash_flow', 'N/A')}

VALUATION:
P/E Trailing: {m.get('pe_trailing', 'N/A')} | P/E Forward: {m.get('pe_forward', 'N/A')}
EV/EBITDA: {m.get('ev_ebitda', 'N/A')} | PEG: {m.get('peg_ratio', 'N/A')} | P/B: {m.get('price_to_book', 'N/A')}
DCF Fair Value: ${dcf.get('fair_value', 'N/A')} (WACC: {dcf.get('wacc', 'N/A')})

QUALITY:
Piotroski F-Score: {q.get('piotroski', {}).get('score', 'N/A')}/9
Altman Z-Score: {q.get('altman_z', {}).get('z_score', 'N/A')} ({q.get('altman_z', {}).get('zone', 'N/A')})

TECHNICAL:
RSI: {t.get('rsi', 'N/A')} ({t.get('rsi_signal', '')}) | MACD: {t.get('macd_signal', 'N/A')}
SMA50: {t.get('sma50', 'N/A')} | SMA200: {t.get('sma200', 'N/A')} | Trend: {t.get('trend', 'N/A')}
Support: {t.get('support', [])} | Resistance: {t.get('resistance', [])}
Volatility: {r.get('volatility', 'N/A')} | Sharpe: {r.get('sharpe', 'N/A')}

GROWTH:
Revenue Growth YoY: {g.get('revenue_growth_yoy', 'N/A')}
Earnings Growth YoY: {g.get('earnings_growth_yoy', 'N/A')}

ANALYST CONSENSUS:
Rating: {a.get('recommendation', 'N/A')} | Target Mean: ${a.get('target_mean', 'N/A')}
Target Range: ${a.get('target_low', 'N/A')} — ${a.get('target_high', 'N/A')} | Analysts: {a.get('analyst_count', 'N/A')}

SCORE: {score_result.get('total_score', 'N/A')}/100 → {score_result.get('rating', 'N/A')}

RECENT NEWS:
{news_summary}"""


def _call_master(master_key: str, data_summary: str) -> dict:
    """Call LLM with a single master's perspective."""
    master = MASTER_PROMPTS[master_key]
    try:
        response = execute_with_fallback(
            messages=[
                {"role": "system", "content": master["system"]},
                {"role": "user", "content": f"Analyze this stock:\n\n{data_summary}"}
            ],
            response_format={"type": "json_object"},
            stream=False
        )
        clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return json.loads(clean)
    except Exception as e:
        return {
            "stars": 3,
            "analysis": f"Analysis unavailable: {str(e)}",
            "error": str(e)
        }


def _synthesize(ticker: str, perspectives: dict, score_result: dict,
                calc_result: dict, raw_data: dict) -> dict:
    """Final LLM call: synthesize 4 perspectives into verdict."""
    p = raw_data.get("price", {})
    dcf = calc_result.get("dcf", {})

    composite = sum(
        perspectives[k].get("stars", 3) for k in perspectives
    ) / len(perspectives)

    perspectives_text = ""
    for key, result in perspectives.items():
        name = MASTER_PROMPTS[key]["name"]
        stars = result.get("stars", 3)
        analysis = result.get("analysis", "N/A")
        perspectives_text += f"\n{name} ({stars}/5 stars):\n{analysis}\n"

    try:
        response = execute_with_fallback(
            messages=[
                {"role": "system", "content": """You are the Team Lead synthesizing 4 investment perspectives into a final verdict.
You have pre-calculated scores and 4 expert analyses. Your job is to:
1. Write a one-sentence thesis (50-100 chars)
2. Create bull case (5 points) and bear case (5 points) — these should show REAL TENSION between perspectives
3. Set 3-scenario target prices based on the DCF and analyst targets provided
4. Make a final decision: Pass / Conditional Pass / Gray Zone
5. Write a concise summary paragraph (100-200 words)

Respond ONLY in valid JSON:
{
  "thesis": "<one sentence investment thesis>",
  "bull_case": ["<point1>", "<point2>", "<point3>", "<point4>", "<point5>"],
  "bear_case": ["<point1>", "<point2>", "<point3>", "<point4>", "<point5>"],
  "scenarios": {
    "bull": {"price": <number>, "probability": "<pct>"},
    "base": {"price": <number>, "probability": "<pct>"},
    "bear": {"price": <number>, "probability": "<pct>"}
  },
  "decision": "<Pass / Conditional Pass / Gray Zone>",
  "action": "<specific actionable recommendation>",
  "summary": "<100-200 word synthesis paragraph>"
}"""},
                {"role": "user", "content": f"""Ticker: {ticker}
Current Price: ${p.get('current', 'N/A')}
AI Score: {score_result.get('total_score', 'N/A')}/100 ({score_result.get('rating', 'N/A')})
DCF Fair Value: ${dcf.get('fair_value', 'N/A')}
Analyst Target: ${raw_data.get('analyst', {}).get('target_mean', 'N/A')}
Composite Stars: {round(composite, 2)}/5

4 EXPERT PERSPECTIVES:
{perspectives_text}
"""}
            ],
            response_format={"type": "json_object"},
            stream=False
        )
        clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return json.loads(clean)
    except Exception as e:
        return {
            "thesis": f"Analysis for {ticker}",
            "decision": "Gray Zone",
            "action": "Insufficient data for recommendation",
            "summary": f"Synthesis failed: {str(e)}",
            "error": str(e)
        }


def analyze(ticker: str, raw_data: dict, calc_result: dict, score_result: dict) -> dict:
    """
    Chạy 4 Masters + tổng hợp. Trả về structured output.
    """
    data_summary = _build_data_summary(raw_data, calc_result, score_result)

    # 4 LLM calls in parallel
    perspectives = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_call_master, key, data_summary): key
            for key in MASTER_PROMPTS
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                perspectives[key] = future.result()
            except Exception as e:
                perspectives[key] = {"stars": 3, "analysis": f"Error: {e}"}

    # 5th LLM call: synthesize
    synthesis = _synthesize(ticker, perspectives, score_result, calc_result, raw_data)

    composite_stars = round(
        sum(perspectives[k].get("stars", 3) for k in perspectives) / 4, 2
    )

    return {
        "ticker": ticker,
        "perspectives": {
            "duan": {
                "name": "Duan Yongping",
                "focus": "Business Essence",
                **perspectives.get("duan", {})
            },
            "buffett": {
                "name": "Warren Buffett",
                "focus": "Valuation & Moat",
                **perspectives.get("buffett", {})
            },
            "munger": {
                "name": "Charlie Munger",
                "focus": "Risks & Inversion",
                **perspectives.get("munger", {})
            },
            "lilu": {
                "name": "Li Lu",
                "focus": "Long-term Trends",
                **perspectives.get("lilu", {})
            },
        },
        "composite_stars": composite_stars,
        "synthesis": synthesis,
    }
