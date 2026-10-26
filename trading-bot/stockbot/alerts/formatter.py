"""Alert message text (Telegram HTML)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from html import escape

from stockbot.data.market import fmt_et, to_et
from stockbot.data.quotes import Quote
from stockbot.strategy.describe import operand_text

_OP_SHORT = {">": ">", "<": "<", ">=": "≥", "<=": "≤", "crosses_above": "crossed above", "crosses_below": "crossed below"}
_EXIT_TITLES = {
    "exit": "sell rule triggered",
    "stop_loss": "stop-loss hit",
    "trailing_stop": "trailing stop hit",
    "take_profit": "take-profit reached",
}
DISCLAIMER = "ℹ️ Notification only — no order was placed. Not financial advice."


@dataclass
class TradePlan:
    stop: float | None
    stop_is_suggested: bool
    target: float | None
    target_is_suggested: bool
    shares: int | None


def build_plan(price: float, stop: float | None, target: float | None, atr: float | None,
               capital: float | None, risk_pct: float | None) -> TradePlan:
    stop_sug = target_sug = False
    if stop is None and atr and atr == atr:
        stop, stop_sug = price - 2 * atr, True
    if target is None and stop is not None and stop < price:
        target, target_sug = price + 2 * (price - stop), True
    shares = None
    if capital and risk_pct and stop is not None and stop < price:
        by_risk = capital * risk_pct / 100 / (price - stop)
        shares = int(max(0, math.floor(min(by_risk, capital / price))))
    return TradePlan(stop, stop_sug, target, target_sug, shares)


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _price_line(q: Quote) -> str:
    if q.source == "official close":
        when = f"🕒 Official close, {to_et(q.traded_at):%b %d %Y}"
    else:
        when = f"🕒 Last trade {fmt_et(q.traded_at)} · {q.source}"
    return f"Price: <b>{_money(q.price)}</b> ({q.change_pct:+.2f}% today)\n{when}"


def _why_lines(explained: list[dict]) -> list[str]:
    out = []
    for row in explained:
        mark = "✅" if row["passed"] else "▫️"
        lv, rv = row["left_value"], row["right_value"]
        values = f" ({lv:,.2f} vs {rv:,.2f})" if lv is not None and rv is not None else ""
        out.append(f"{mark} {escape(operand_text(row['left']))} {_OP_SHORT[row['op']]} "
                   f"{escape(operand_text(row['right']))}{values}")
    return out


def _backtest_line(last_backtest: dict | None, ticker: str) -> str | None:
    if not last_backtest:
        return None
    stats = (last_backtest.get("per_ticker") or {}).get(ticker) or last_backtest.get("portfolio")
    if not stats or not stats.get("total_trades"):
        return None
    period = last_backtest.get("period", {})
    span = f"{period.get('start', '?')} → {period.get('end', '?')}"
    return (f"📊 Backtest {span}: win rate {stats['win_rate_pct']}% · avg trade {stats['avg_trade_pct']:+}% · "
            f"{stats['total_trades']} trades")


def entry_message(strategy_name: str, ticker: str, q: Quote, explained: list[dict], plan: TradePlan,
                  last_backtest: dict | None, intraday: bool, risk_pct: float | None) -> str:
    lines = [f"🟢 <b>BUY signal — {escape(ticker)}</b>", f"Strategy: <b>{escape(strategy_name)}</b>",
             _price_line(q), "", "<b>Why</b>", *_why_lines(explained)]
    plan_lines = []
    if plan.stop is not None:
        tag = " (suggested: 2×ATR)" if plan.stop_is_suggested else ""
        plan_lines.append(f"• Stop-loss: {_money(plan.stop)} ({(plan.stop / q.price - 1) * 100:+.1f}%){tag}")
    if plan.target is not None:
        tag = " (suggested: 2R)" if plan.target_is_suggested else ""
        rr = ""
        if plan.stop is not None and plan.stop < q.price:
            rr = f" · reward/risk {(plan.target - q.price) / (q.price - plan.stop):.1f}"
        plan_lines.append(f"• Target: {_money(plan.target)} ({(plan.target / q.price - 1) * 100:+.1f}%){rr}{tag}")
    if plan.shares is not None:
        plan_lines.append(f"• Size: ~{plan.shares} shares (risking {risk_pct:g}% of your capital)")
    if plan_lines:
        lines += ["", "<b>Plan</b>", *plan_lines]
    bt = _backtest_line(last_backtest, ticker)
    if bt:
        lines += ["", bt]
    lines += ["", "⏱ Intraday signal — re-checked at the close." if intraday else "✔️ Confirmed on the closing price.",
              DISCLAIMER]
    return "\n".join(lines)


def exit_message(strategy_name: str, ticker: str, q: Quote, kind: str, level: float | None,
                 entry_price: float, entry_date: date, sessions_held: int, explained: list[dict] | None) -> str:
    ref = level if level is not None and kind != "exit" else q.price
    pnl = (ref / entry_price - 1) * 100
    lines = [f"🔴 <b>SELL signal — {escape(ticker)}</b> ({_EXIT_TITLES[kind]})",
             f"Strategy: <b>{escape(strategy_name)}</b>", _price_line(q)]
    if level is not None and kind != "exit":
        lines.append(f"Level: {_money(level)}")
    lines.append(f"Since the BUY alert on {entry_date:%b %d} at {_money(entry_price)}: <b>{pnl:+.2f}%</b> "
                 f"({sessions_held} session(s))")
    if explained:
        lines += ["", "<b>Why</b>", *_why_lines(explained)]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def invalidated_message(strategy_name: str, ticker: str, q: Quote, entry_price: float) -> str:
    return "\n".join([
        f"⚪ <b>Signal cancelled — {escape(ticker)}</b>",
        f"Strategy: <b>{escape(strategy_name)}</b>",
        f"Today's intraday BUY alert at {_money(entry_price)} is <b>no longer valid</b>: "
        f"the conditions are not met on the closing price.",
        _price_line(q),
        DISCLAIMER,
    ])


def chart_button(ticker: str) -> list[list[dict]]:
    return [[{"text": f"📈 {ticker} chart", "url": f"https://finance.yahoo.com/quote/{ticker}/chart"}]]
