"""US market clock helpers (America/New_York)."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)


def now_et() -> datetime:
    return datetime.now(timezone.utc).astimezone(ET)


def to_et(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET)


def is_regular_hours_clock(at: datetime | None = None) -> bool:
    """Weekday 09:30–16:00 ET. Does not know holidays — prefer Finnhub market status."""
    at = to_et(at) if at else now_et()
    return at.weekday() < 5 and REGULAR_OPEN <= at.time() < REGULAR_CLOSE


def session_date(at: datetime | None = None) -> date:
    return (to_et(at) if at else now_et()).date()


def fmt_et(ts: datetime) -> str:
    return to_et(ts).strftime("%H:%M:%S ET, %b %d %Y")
