"""User-scoped operations behind the MCP tools. Every function takes the authenticated user id.

Nothing here can place orders: the system only analyses and notifies.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from stockbot.alerts.formatter import DISCLAIMER
from stockbot.alerts.notifier import user_bot
from stockbot.backtest.chart import backtest_chart
from stockbot.backtest.runner import BacktestError, parse_period, run_backtest
from stockbot.config import settings
from stockbot.data.history import get_daily
from stockbot.data.live import with_live_bar
from stockbot.data.market import fmt_et, to_et
from stockbot.data.quotes import QuoteError, get_quote, market_status
from stockbot.store.db import session_scope
from stockbot.store.models import BotUser, MutedTicker, Position, SignalEvent, StrategyRow
from stockbot.store.security import hash_api_key
from stockbot.strategy.describe import describe
from stockbot.strategy.dsl import PRESETS, Strategy, parse_strategy, strategy_json_schema, warmup_bars
from stockbot.strategy.engine import Evaluator, explain_at

log = logging.getLogger(__name__)


class UserError(ValueError):
    """A problem the user/agent can fix; the message is shown to them."""


def authenticate(api_key: str) -> int:
    with session_scope() as s:
        user = s.scalar(select(BotUser).where(BotUser.api_key_hash == hash_api_key(api_key)))
        if user is None or user.status == "stopped":
            raise PermissionError("invalid API key")
        return user.id


# ---------------------------------------------------------------- helpers
def _strategy_row(s, user_id: int, strategy_id: int) -> StrategyRow:
    row = s.get(StrategyRow, strategy_id)
    if row is None or row.user_id != user_id or row.status == "archived":
        raise UserError(f"Strategy #{strategy_id} not found")
    return row


def _parse_or_raise(dsl: dict) -> Strategy:
    strat, errors = parse_strategy(dsl)
    if strat is None:
        raise UserError("Invalid strategy:\n- " + "\n- ".join(errors))
    if len(strat.universe.resolve()) > settings.max_tickers_per_strategy:
        raise UserError(f"At most {settings.max_tickers_per_strategy} tickers per strategy")
    return strat


def _summary(row: StrategyRow) -> dict:
    bt = row.last_backtest or {}
    pf = bt.get("portfolio") or {}
    return {
        "id": row.id, "name": row.name, "status": row.status, "version": row.version,
        "tickers": (row.dsl.get("universe") or {}).get("tickers", []),
        "last_backtest": {"period": bt.get("period"), "total_return_pct": pf.get("total_return_pct"),
                          "win_rate_pct": pf.get("win_rate_pct"), "trades": pf.get("total_trades")} if bt else None,
        "alerts_on_since": row.activated_at.isoformat() if row.activated_at and row.status == "active" else None,
    }


# ---------------------------------------------------------------- strategy authoring
def schema() -> dict:
    return {
        "json_schema": strategy_json_schema(),
        "presets": PRESETS,
        "notes": [
            "Daily candles only. Signals use the daily close; backtest fills at the next open.",
            "'highest'/'lowest' look at the PRIOR n days, so `close > highest(20)` is a 20-day breakout.",
            "pct_change is in percent (5 means +5%). bb_width is in percent of the middle band.",
            "Numbers can be compared with prices/indicators; two plain numbers cannot be compared.",
        ],
        "example": {
            "name": "RSI rebound above 200-day MA",
            "universe": {"tickers": ["AAPL", "MSFT"]},
            "entry": {"all": [
                {"left": {"ind": "rsi", "period": 14}, "op": "crosses_above", "right": 30},
                {"left": {"price": "close"}, "op": ">", "right": {"ind": "sma", "period": 200}},
            ]},
            "exit": {"left": {"ind": "rsi", "period": 14}, "op": ">", "right": 70},
            "risk": {"stop_loss_pct": 7, "take_profit_pct": 15},
        },
    }


def validate(dsl: dict) -> dict:
    strat = _parse_or_raise(dsl)
    return {"valid": True, "summary": describe(strat), "normalized": strat.model_dump(by_alias=True, exclude_none=True)}


def save_strategy(user_id: int, dsl: dict) -> dict:
    strat = _parse_or_raise(dsl)
    with session_scope() as s:
        count = s.scalar(select(func.count()).select_from(StrategyRow).where(
            StrategyRow.user_id == user_id, StrategyRow.status != "archived"))
        if count >= settings.max_strategies_per_user:
            raise UserError(f"You can keep at most {settings.max_strategies_per_user} strategies. Delete one first.")
        row = StrategyRow(user_id=user_id, name=strat.name, dsl=strat.model_dump(by_alias=True, exclude_none=True))
        s.add(row)
        s.flush()
        return {"saved": True, **_summary(row), "summary": describe(strat)}


def update_strategy(user_id: int, strategy_id: int, dsl: dict) -> dict:
    strat = _parse_or_raise(dsl)
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        row.dsl = strat.model_dump(by_alias=True, exclude_none=True)
        row.name = strat.name
        row.version += 1
        row.last_backtest = None  # old results no longer describe this strategy
        return {"updated": True, **_summary(row), "summary": describe(strat),
                "note": "Run a new backtest — the previous result was for the old version."}


def list_strategies(user_id: int) -> dict:
    with session_scope() as s:
        rows = s.scalars(select(StrategyRow).where(StrategyRow.user_id == user_id, StrategyRow.status != "archived")
                         .order_by(StrategyRow.id)).all()
        return {"strategies": [_summary(r) for r in rows]}


def get_strategy(user_id: int, strategy_id: int) -> dict:
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        strat = _parse_or_raise(row.dsl)
        muted = s.scalars(select(MutedTicker.ticker).where(MutedTicker.strategy_id == row.id)).all()
        return {**_summary(row), "summary": describe(strat), "dsl": row.dsl, "muted_tickers": list(muted),
                "last_backtest": row.last_backtest}


def delete_strategy(user_id: int, strategy_id: int) -> dict:
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        row.status = "archived"
        for p in s.scalars(select(Position).where(Position.strategy_id == row.id, Position.status == "open")):
            p.status, p.exit_reason = "void", "strategy_deleted"
        return {"deleted": True, "id": strategy_id}


def set_alerts(user_id: int, strategy_id: int, on: bool) -> dict:
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        if on:
            _parse_or_raise(row.dsl)
            row.status = "active"
            row.activated_at = datetime.now(timezone.utc)
        else:
            row.status = "paused"
        status = market_status()
        return {
            **_summary(row),
            "message": (f"Alerts ON for '{row.name}'. I check every {settings.check_interval_minutes} minutes during "
                        "US market hours (9:30–16:00 ET) and once more on the closing price."
                        if on else f"Alerts paused for '{row.name}'."),
            "market_now": status.session,
        }


def mute_ticker(user_id: int, strategy_id: int, ticker: str, muted: bool) -> dict:
    ticker = ticker.strip().upper()
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        existing = s.scalar(select(MutedTicker).where(MutedTicker.strategy_id == row.id, MutedTicker.ticker == ticker))
        if muted and not existing:
            s.add(MutedTicker(strategy_id=row.id, ticker=ticker))
        elif not muted and existing:
            s.delete(existing)
        return {"strategy_id": row.id, "ticker": ticker, "muted": muted}


# ---------------------------------------------------------------- backtest
def backtest(user_id: int, strategy_id: int | None = None, dsl: dict | None = None, period: str | None = "3y",
             start: str | None = None, end: str | None = None, capital: float = 10_000.0,
             send_chart: bool = True) -> dict:
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id) if strategy_id else None
        strat = _parse_or_raise(row.dsl if row else (dsl or {}))
        user = s.get(BotUser, user_id)
    try:
        s_date, e_date = parse_period(period, start, end)
        result = run_backtest(strat, s_date, e_date, capital=max(100.0, min(capital, 1e9)))
    except BacktestError as e:
        raise UserError(str(e)) from e

    out = result.to_dict()
    out["summary"] = describe(strat)
    if row is not None:
        with session_scope() as s:
            r = s.get(StrategyRow, row.id)
            r.last_backtest = {"period": out["period"], "portfolio": out["portfolio"], "per_ticker": out["per_ticker"]}

    if send_chart and user is not None and user.bot_token_enc:
        pf = out["portfolio"]
        caption = (f"<b>{strat.name}</b>\n{out['period']['start']} → {out['period']['end']}\n"
                   f"Return {pf['total_return_pct']:+}% vs buy &amp; hold {pf['buy_hold_return_pct']:+}%\n"
                   f"Win rate {pf['win_rate_pct']}% · {pf['total_trades']} trades · max drawdown {pf['max_drawdown_pct']}%")
        try:
            user_bot(user).send_photo(user.telegram_user_id, backtest_chart(result), caption=caption)
            out["chart"] = "sent to the user's Telegram chat"
        except Exception as e:  # chart is a bonus; never fail the backtest for it
            log.warning("backtest chart not sent: %s", e)
            out["chart"] = "not sent"
    out["disclaimer"] = "Past performance does not guarantee future results. " + DISCLAIMER
    return out


# ---------------------------------------------------------------- live data
def quote(ticker: str) -> dict:
    try:
        q = get_quote(ticker.strip().upper())
    except QuoteError as e:
        raise UserError(str(e)) from e
    status = market_status()
    return {
        "ticker": q.symbol, "price": q.price, "change_pct_today": round(q.change_pct, 2),
        "open": q.open, "high": q.high, "low": q.low, "prev_close": q.prev_close,
        "last_trade_time": fmt_et(q.traded_at), "age_seconds": int(q.age_seconds()),
        "source": q.source, "market_session": status.session,
    }


def scan_now(user_id: int, strategy_id: int) -> dict:
    """Which tickers meet the BUY / SELL rules right now, on the live timestamped price."""
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        strat = _parse_or_raise(row.dsl)
    tickers = strat.universe.resolve()
    today = to_et(datetime.now(timezone.utc)).date()
    history = get_daily(tickers, today - timedelta(days=int(warmup_bars(strat) * 1.5) + 30), today)
    results = []
    for t in tickers:
        item: dict = {"ticker": t}
        try:
            q = get_quote(t)
        except QuoteError as e:
            results.append({**item, "error": str(e)})
            continue
        hist = history.get(t)
        if hist is None or hist.empty:
            results.append({**item, "error": "no price history"})
            continue
        frame = with_live_bar(hist, q)
        ev = Evaluator(frame)
        item.update({
            "price": q.price, "last_trade_time": fmt_et(q.traded_at), "source": q.source,
            "buy_rule_met": bool(ev.condition(strat.entry).iloc[-1]),
            "sell_rule_met": bool(ev.condition(strat.exit).iloc[-1]) if strat.exit is not None else None,
            "buy_conditions": [
                {"passed": r["passed"], "left_value": r["left_value"], "right_value": r["right_value"]}
                for r in explain_at(frame, strat.entry)
            ],
        })
        results.append(item)
    return {"strategy": strat.name, "market_session": market_status().session, "results": results,
            "note": "Today's candle uses the live price; it becomes final at the 16:00 ET close."}


# ---------------------------------------------------------------- history & tracking
def list_signals(user_id: int, strategy_id: int | None = None, days: int = 14) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))
    with session_scope() as s:
        q = (select(SignalEvent, StrategyRow.name).join(StrategyRow, SignalEvent.strategy_id == StrategyRow.id)
             .where(StrategyRow.user_id == user_id, SignalEvent.created_at >= since))
        if strategy_id:
            q = q.where(SignalEvent.strategy_id == strategy_id)
        rows = s.execute(q.order_by(SignalEvent.created_at.desc()).limit(50)).all()
        return {"signals": [{
            "strategy": name, "strategy_id": ev.strategy_id, "ticker": ev.ticker, "kind": ev.kind,
            "price": ev.price, "price_time": fmt_et(ev.price_time), "source": ev.source, "delivered": ev.delivered,
        } for ev, name in rows]}


def tracking(user_id: int, strategy_id: int) -> dict:
    """Forward performance since alerts were turned on (based on alert prices)."""
    with session_scope() as s:
        row = _strategy_row(s, user_id, strategy_id)
        positions = s.scalars(select(Position).where(Position.strategy_id == row.id,
                                                     Position.status.in_(("open", "closed")))).all()
        open_items, closed = [], []
        for p in positions:
            if p.status == "closed":
                closed.append({"ticker": p.ticker, "entry": p.entry_price, "exit": p.exit_price,
                               "return_pct": round((p.exit_price / p.entry_price - 1) * 100, 2),
                               "entry_date": p.entry_date.isoformat(), "exit_date": p.exit_date.isoformat(),
                               "reason": p.exit_reason})
            else:
                open_items.append({"ticker": p.ticker, "entry": p.entry_price, "entry_date": p.entry_date.isoformat(),
                                   "stop": p.stop, "target": p.target})
        rets = [c["return_pct"] for c in closed]
        return {
            "strategy": row.name, "open_signals": open_items, "closed_signals": closed[-20:],
            "closed_count": len(closed),
            "win_rate_pct": round(sum(r > 0 for r in rets) / len(rets) * 100, 1) if rets else None,
            "avg_return_pct": round(sum(rets) / len(rets), 2) if rets else None,
            "note": "Hypothetical: assumes you acted at each alert price.",
        }


def set_preferences(user_id: int, capital: float | None = None, risk_pct: float | None = None) -> dict:
    with session_scope() as s:
        user = s.get(BotUser, user_id)
        if capital is not None:
            if capital <= 0:
                raise UserError("Capital must be positive")
            user.capital = capital
        if risk_pct is not None:
            if not 0 < risk_pct <= 10:
                raise UserError("Risk per trade must be between 0 and 10 percent")
            user.risk_pct = risk_pct
        return {"capital": user.capital, "risk_pct": user.risk_pct,
                "note": "Used only to suggest position sizes in alerts."}
