"""Scheduled strategy checks: live timestamped price → same evaluation as the backtest → alert.

Accuracy rules:
- Only prices with an exchange timestamp from *today's* session are used.
- Intraday, a price older than MAX_QUOTE_AGE_SECONDS is rejected (no alert), never guessed.
- The close run uses the official daily close (completed daily candle, published ~16:20 ET) and
  confirms or cancels intraday entry alerts. It never uses after-hours prints.
- Each (strategy, ticker, kind, session) can alert at most once.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Callable

import pandas as pd
from sqlalchemy import select

from stockbot.alerts import formatter
from stockbot.backtest.chart import alert_chart
from stockbot.backtest.simulator import stop_levels
from stockbot.config import settings
from stockbot.data.history import get_daily, invalidate
from stockbot.data.live import with_live_bar
from stockbot.data.market import ET, to_et
from stockbot.data.quotes import MarketStatus, Quote, get_quotes, market_status
from stockbot.store.db import session_scope
from stockbot.store.models import BotUser, CheckRun, MutedTicker, Position, SignalEvent, StrategyRow, utcnow
from stockbot.strategy import indicators
from stockbot.strategy.dsl import Strategy, parse_strategy, warmup_bars
from stockbot.strategy.engine import Evaluator, explain_at

log = logging.getLogger(__name__)

CLOSE_TIME = time(16, 0)


@dataclass
class Alert:
    user_id: int
    ticker: str
    text: str
    chart: bytes | None = None
    event_id: int | None = None


@dataclass
class CheckReport:
    mode: str
    skipped: str | None = None
    tickers: int = 0
    alerts: list[Alert] = field(default_factory=list)
    stale: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


Sender = Callable[[BotUser, Alert], bool]


def _sessions_between(frame: pd.DataFrame, start, end) -> int:
    idx = frame.index
    return int(((idx > pd.Timestamp(start)) & (idx <= pd.Timestamp(end))).sum())


def _quote_problem(q: Quote, today, now: datetime) -> str | None:
    traded = to_et(q.traded_at)
    if traded.date() != today:
        return f"last trade is from {traded:%Y-%m-%d}, not today"
    age = q.age_seconds(now)
    if age > settings.max_quote_age_seconds:
        return f"price is {int(age)}s old (limit {settings.max_quote_age_seconds}s)"
    return None


def close_quote(ticker: str, daily: pd.DataFrame, today) -> Quote | None:
    """A Quote built from today's official daily candle (None if it is not published yet)."""
    if daily is None or len(daily) < 2 or daily.index[-1].date() != today:
        return None
    last, prev = daily.iloc[-1], daily.iloc[-2]
    at = datetime.combine(today, CLOSE_TIME, tzinfo=ET).astimezone(timezone.utc)
    return Quote(symbol=ticker, price=float(last["Close"]), open=float(last["Open"]), high=float(last["High"]),
                 low=float(last["Low"]), prev_close=float(prev["Close"]), traded_at=at, fetched_at=utcnow(),
                 source="official close")


def run_check(
    mode: str = "intraday",
    *,
    force: bool = False,
    now: datetime | None = None,
    status_fn: Callable[[], MarketStatus] = market_status,
    quotes_fn: Callable[[list[str]], tuple[dict[str, Quote], dict[str, str]]] = get_quotes,
    history_fn=get_daily,
    sender: Sender | None = None,
    render_charts: bool = True,
) -> CheckReport:
    assert mode in ("intraday", "close")
    now = now or datetime.now(timezone.utc)
    today = to_et(now).date()
    report = CheckReport(mode=mode)

    if mode == "intraday" and not force:
        status = status_fn()
        if not status.is_open:
            report.skipped = f"market not in regular session ({status.session}{', ' + status.holiday if status.holiday else ''})"
            return report

    with session_scope() as s:
        rows = s.execute(
            select(StrategyRow, BotUser).join(BotUser, StrategyRow.user_id == BotUser.id)
            .where(StrategyRow.status == "active", BotUser.status == "active")
        ).all()
        muted = {(m.strategy_id, m.ticker) for m in s.scalars(select(MutedTicker))}
        open_positions = {(p.strategy_id, p.ticker): p for p in s.scalars(select(Position).where(Position.status == "open"))}

        plans: list[tuple[StrategyRow, BotUser, Strategy, list[str]]] = []
        for row, user in rows:
            strat, errs = parse_strategy(row.dsl)
            if strat is None:
                report.errors[f"strategy:{row.id}"] = "; ".join(errs)
                continue
            tickers = [t for t in strat.universe.resolve() if (row.id, t) not in muted]
            plans.append((row, user, strat, tickers))

        active_ids = {p[0].id for p in plans}
        open_positions = {k: v for k, v in open_positions.items() if k[0] in active_ids}
        all_tickers = sorted({t for *_, ts in plans for t in ts})
        report.tickers = len(all_tickers)
        if not all_tickers:
            report.skipped = "no active strategies"
            return report

        if mode == "close":
            invalidate(all_tickers)
        longest = max((warmup_bars(p[2]) for p in plans), default=60)
        history = history_fn(all_tickers, today - timedelta(days=int(longest * 1.5) + 30), today)
        frames: dict[str, pd.DataFrame] = {}
        if mode == "close":
            quotes = {}
            for t in all_tickers:
                q = close_quote(t, history.get(t), today)
                if q is None:
                    report.stale[t] = "official close not published yet (or no session today)"
                    continue
                quotes[t], frames[t] = q, history[t]
        else:
            quotes, q_errors = quotes_fn(all_tickers)
            report.errors.update(q_errors)
            for t in all_tickers:
                q = quotes.get(t)
                if q is None:
                    continue
                problem = _quote_problem(q, today, now)
                if problem:
                    report.stale[t] = problem
                    continue
                hist = history.get(t)
                if hist is None or hist.empty:
                    report.errors[t] = "no price history"
                    continue
                frames[t] = with_live_bar(hist, q)

        for row, user, strat, tickers in plans:
            for t in tickers:
                if t not in frames:
                    continue
                frame, q = frames[t], quotes[t]
                if len(frame) < warmup_bars(strat):
                    report.errors[t] = "not enough history for this strategy's indicators"
                    continue
                alert = _check_one(s, row, user, strat, t, frame, q, mode, today, open_positions, render_charts)
                if alert:
                    report.alerts.append(alert)

        s.add(CheckRun(mode=mode, finished_at=utcnow(), tickers=report.tickers, alerts=len(report.alerts),
                       stale=report.stale or None, errors=report.errors or None))

    if sender:
        with session_scope() as s:
            users = {u.id: u for u in s.scalars(select(BotUser).where(BotUser.id.in_({a.user_id for a in report.alerts})))}
        for a in report.alerts:
            try:
                ok = sender(users[a.user_id], a)
            except Exception:  # one failed delivery must not stop the others
                log.exception("alert delivery failed for user %s %s", a.user_id, a.ticker)
                ok = False
            if ok and a.event_id:
                with session_scope() as s:
                    ev = s.get(SignalEvent, a.event_id)
                    if ev:
                        ev.delivered = True
    return report


def _record(s, row: StrategyRow, ticker: str, kind: str, today, q: Quote, details: dict) -> int | None:
    """Insert the signal event; None if this alert was already produced this session."""
    exists = s.scalar(select(SignalEvent.id).where(
        SignalEvent.strategy_id == row.id, SignalEvent.ticker == ticker,
        SignalEvent.kind == kind, SignalEvent.session == today))
    if exists:
        return None
    ev = SignalEvent(strategy_id=row.id, ticker=ticker, kind=kind, session=today, price=q.price,
                     price_time=q.traded_at, source=q.source, details=details, delivered=False)
    s.add(ev)
    s.flush()
    return ev.id


def _check_one(s, row, user, strat: Strategy, ticker: str, frame: pd.DataFrame, q: Quote, mode: str, today,
               open_positions: dict, render_charts: bool) -> Alert | None:
    ev = Evaluator(frame)
    entry_now = bool(ev.condition(strat.entry).iloc[-1])
    exit_now = bool(ev.condition(strat.exit).iloc[-1]) if strat.exit is not None else False
    pos: Position | None = open_positions.get((row.id, ticker))
    wants = set(strat.alert.on)

    # ---- no open position: look for an entry -----------------------------------
    if pos is None:
        if not entry_now:
            return None
        last_closed = s.scalar(select(Position).where(
            Position.strategy_id == row.id, Position.ticker == ticker, Position.status == "closed",
        ).order_by(Position.exit_date.desc()).limit(1))
        if last_closed and last_closed.exit_date and \
                _sessions_between(frame, last_closed.exit_date, today) <= strat.alert.cooldown_bars:
            return None
        atr_series = indicators.atr(frame, 14)
        atr_now = float(atr_series.iloc[-1]) if atr_series.notna().iloc[-1] else None
        stop, target = stop_levels(strat, q.price, atr_now)
        explained = explain_at(frame, strat.entry)
        event_id = _record(s, row, ticker, "entry", today, q, {"mode": mode, "conditions": _jsonable(explained)})
        if event_id is None:
            return None
        pos = Position(strategy_id=row.id, ticker=ticker, status="open", provisional=(mode == "intraday"),
                       entry_date=today, entry_price=q.price, entry_time=q.traded_at,
                       stop=stop, target=target, peak=q.price)
        s.add(pos)
        open_positions[(row.id, ticker)] = pos
        if "entry" not in wants:
            return None
        plan = formatter.build_plan(q.price, stop, target, atr_now, user.capital, user.risk_pct)
        text = formatter.entry_message(row.name, ticker, q, explained, plan, row.last_backtest,
                                       intraday=(mode == "intraday"), risk_pct=user.risk_pct)
        return Alert(user.id, ticker, text, _chart(frame, ticker, q.price, plan.stop, plan.target) if render_charts else None,
                     event_id)

    # ---- intraday entry re-checked on the close ----------------------------------
    if mode == "close" and pos.provisional and pos.entry_date == today:
        if not entry_now:
            pos.status, pos.exit_reason = "void", "invalidated"
            open_positions.pop((row.id, ticker), None)
            event_id = _record(s, row, ticker, "invalidated", today, q, {"entry_price": pos.entry_price})
            if event_id is not None and "entry" in wants:
                return Alert(user.id, ticker, formatter.invalidated_message(row.name, ticker, q, pos.entry_price),
                             event_id=event_id)
            return None
        pos.provisional = False

    # ---- open position: risk exits, then the sell rule -----------------------------
    entered_today = pos.entry_date == today
    # If the position was opened today, today's earlier high/low may pre-date the alert: use the live price only.
    low = q.price if entered_today else min(q.low, q.price)
    high = q.price if entered_today else max(q.high, q.price)
    kind, level = None, None
    eff_stop, stop_kind = pos.stop, "stop_loss"
    if strat.risk.trailing_stop_pct:
        trail = pos.peak * (1 - strat.risk.trailing_stop_pct / 100)
        if eff_stop is None or trail > eff_stop:
            eff_stop, stop_kind = trail, "trailing_stop"
    if eff_stop is not None and low <= eff_stop:
        kind, level = stop_kind, eff_stop
    elif pos.target is not None and high >= pos.target:
        kind, level = "take_profit", pos.target
    elif exit_now:
        kind = "exit"
    else:
        pos.peak = max(pos.peak, high)
        return None

    explained = explain_at(frame, strat.exit) if kind == "exit" and strat.exit is not None else None
    event_id = _record(s, row, ticker, kind, today, q, {"mode": mode, "level": level,
                                                         "conditions": _jsonable(explained) if explained else None})
    if event_id is None:
        return None
    pos.status, pos.exit_date, pos.exit_reason = "closed", today, kind
    pos.exit_price = level if level is not None else q.price
    open_positions.pop((row.id, ticker), None)
    if "exit" not in wants:
        return None
    text = formatter.exit_message(row.name, ticker, q, kind, level, pos.entry_price, pos.entry_date,
                                  _sessions_between(frame, pos.entry_date, today), explained)
    return Alert(user.id, ticker, text, _chart(frame, ticker, q.price, pos.stop, pos.target) if render_charts else None,
                 event_id)


def _chart(frame: pd.DataFrame, ticker: str, price: float, stop: float | None, target: float | None) -> bytes | None:
    try:
        overlays = {"MA50": indicators.sma(frame["Close"], 50), "MA200": indicators.sma(frame["Close"], 200)}
        return alert_chart(frame, ticker, price, stop, target, overlays)
    except Exception:
        log.exception("chart rendering failed for %s", ticker)
        return None


def _jsonable(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        r = dict(r)
        for k in ("left", "right"):
            v = r[k]
            r[k] = v if isinstance(v, (int, float)) else v.model_dump(by_alias=True, exclude_defaults=True)
        out.append(r)
    return out
