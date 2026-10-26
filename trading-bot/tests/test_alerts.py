from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select

from conftest import make_ohlc
from stockbot.alerts.engine import run_check
from stockbot.data.market import ET
from stockbot.data.quotes import Quote
from stockbot.store.db import session_scope
from stockbot.store.models import BotUser, Position, SignalEvent, StrategyRow

TODAY = datetime(2026, 10, 27, tzinfo=ET).date()        # a Tuesday
NOW = datetime(2026, 10, 27, 10, 30, tzinfo=ET).astimezone(timezone.utc)

STRATEGY = {
    "name": "Breakout", "universe": {"tickers": ["AAA"]},
    "entry": {"left": {"price": "close"}, "op": "crosses_above", "right": 105},
    "exit": {"left": {"price": "close"}, "op": "crosses_below", "right": 95},
    "risk": {"stop_loss_pct": 5},
}


def history() -> pd.DataFrame:
    # 60 completed sessions at 100, ending yesterday.
    idx = pd.bdate_range(end=pd.Timestamp(TODAY) - pd.Timedelta(days=1), periods=60)
    df = make_ohlc([100.0] * 60)
    df.index = idx
    return df


def quote(price: float, at: datetime = NOW, low: float | None = None) -> Quote:
    return Quote("AAA", price, 100.0, max(price, 100.0), low if low is not None else min(price, 100.0), 100.0, at, NOW)


def setup_user() -> int:
    with session_scope() as s:
        u = BotUser(telegram_user_id=111, status="active", bot_username="x_bot")
        s.add(u)
        s.flush()
        row = StrategyRow(user_id=u.id, name="Breakout", dsl=STRATEGY, status="active")
        s.add(row)
        s.flush()
        return row.id


def run(q: Quote, mode="intraday", now=NOW, hist=None):
    return run_check(mode, force=True, now=now, quotes_fn=lambda t: ({"AAA": q}, {}),
                     history_fn=lambda t, s, e: {"AAA": hist if hist is not None else history()},
                     render_charts=False)


def test_entry_alert_once_per_session(fresh_db):
    setup_user()
    rep = run(quote(106))
    assert len(rep.alerts) == 1
    text = rep.alerts[0].text
    assert "BUY signal — AAA" in text and "$106.00" in text and "10:30:00 ET" in text and "Finnhub" in text
    assert "Stop-loss: $100.70" in text  # 5% below the alert price
    assert len(run(quote(107)).alerts) == 0  # position open → no duplicate entry alert


def test_stale_quote_is_never_used(fresh_db):
    setup_user()
    rep = run(quote(106, at=NOW - timedelta(minutes=20)))
    assert rep.alerts == [] and "AAA" in rep.stale
    yesterday = NOW - timedelta(days=1)
    rep = run(quote(106, at=yesterday))
    assert rep.alerts == [] and "not today" in rep.stale["AAA"]


def test_stop_loss_alert_next_day(fresh_db):
    sid = setup_user()
    run(quote(106))
    next_now = NOW + timedelta(days=1)
    hist = history()
    hist.loc[pd.Timestamp(TODAY)] = [100, 106, 100, 106, 1e6]
    rep = run(quote(101, at=next_now, low=100.5), now=next_now, hist=hist.sort_index())
    assert len(rep.alerts) == 1 and "stop-loss hit" in rep.alerts[0].text
    with session_scope() as s:
        p = s.scalar(select(Position).where(Position.strategy_id == sid))
        assert p.status == "closed" and p.exit_reason == "stop_loss" and round(p.exit_price, 2) == 100.70


def test_close_check_cancels_intraday_signal(fresh_db):
    setup_user()
    run(quote(106))
    hist = history()
    hist.loc[pd.Timestamp(TODAY)] = [100, 106, 100, 104, 1e6]  # official close back below 105
    close_now = datetime(2026, 10, 27, 16, 35, tzinfo=ET).astimezone(timezone.utc)
    rep = run(quote(104), mode="close", now=close_now, hist=hist.sort_index())
    assert len(rep.alerts) == 1 and "Signal cancelled" in rep.alerts[0].text
    with session_scope() as s:
        kinds = sorted(e.kind for e in s.scalars(select(SignalEvent)))
        assert kinds == ["entry", "invalidated"]


def test_close_check_waits_for_official_close(fresh_db):
    setup_user()
    close_now = datetime(2026, 10, 27, 16, 35, tzinfo=ET).astimezone(timezone.utc)
    rep = run(quote(106), mode="close", now=close_now)  # history has no candle for today yet
    assert rep.alerts == [] and "official close not published" in rep.stale["AAA"]


def test_delivery_is_tracked(fresh_db):
    setup_user()
    sent = []
    run_check("intraday", force=True, now=NOW, quotes_fn=lambda t: ({"AAA": quote(106)}, {}),
              history_fn=lambda t, s, e: {"AAA": history()}, render_charts=False,
              sender=lambda user, alert: sent.append(alert) or True)
    assert len(sent) == 1
    with session_scope() as s:
        assert s.scalar(select(SignalEvent)).delivered is True
