"""Real-time quotes from Finnhub, with exchange timestamps.

Every quote carries the time of the last trade (`t` from Finnhub), so alerts can show
exactly which price at which moment triggered them, and stale prices can be rejected.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from stockbot.config import settings
from stockbot.data.market import is_regular_hours_clock

log = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"


class QuoteError(RuntimeError):
    pass


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float          # last trade price
    open: float           # today's open
    high: float           # today's high
    low: float            # today's low
    prev_close: float
    traded_at: datetime   # UTC time of the last trade (exchange timestamp)
    fetched_at: datetime  # UTC time we received it
    source: str = "Finnhub"

    def age_seconds(self, now: datetime | None = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.traded_at).total_seconds()

    @property
    def change_pct(self) -> float:
        return (self.price / self.prev_close - 1) * 100 if self.prev_close else 0.0


class _RateLimiter:
    """Sliding-window limiter: at most `per_minute` calls in any 60 s window."""

    def __init__(self, per_minute: int):
        self.per_minute = max(1, per_minute)
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._calls = [c for c in self._calls if now - c < 60]
                if len(self._calls) < self.per_minute:
                    self._calls.append(now)
                    return
                sleep_for = 60 - (now - self._calls[0]) + 0.05
            time.sleep(sleep_for)


_limiter = _RateLimiter(settings.finnhub_calls_per_minute)


def to_finnhub_symbol(ticker: str) -> str:
    # Yahoo uses BRK-B, Finnhub uses BRK.B
    return ticker.replace("-", ".")


def _get(path: str, params: dict, client: httpx.Client | None = None) -> dict:
    if not settings.finnhub_api_key:
        raise QuoteError("FINNHUB_API_KEY is not configured")
    _limiter.wait()
    params = {**params, "token": settings.finnhub_api_key}
    for attempt in range(3):
        try:
            if client is not None:
                resp = client.get(f"{BASE_URL}{path}", params=params, timeout=10)
            else:
                resp = httpx.get(f"{BASE_URL}{path}", params=params, timeout=10)
        except httpx.HTTPError as e:
            if attempt == 2:
                raise QuoteError(f"Network error calling Finnhub: {e}") from e
            time.sleep(1 + attempt)
            continue
        if resp.status_code == 429:
            time.sleep(2 + 2 * attempt)
            continue
        if resp.status_code != 200:
            raise QuoteError(f"Finnhub returned HTTP {resp.status_code}")
        return resp.json()
    raise QuoteError("Finnhub rate limit reached (429)")


def get_quote(ticker: str, client: httpx.Client | None = None) -> Quote:
    data = _get("/quote", {"symbol": to_finnhub_symbol(ticker)}, client)
    price, ts = data.get("c"), data.get("t")
    if not price or not ts:
        raise QuoteError(f"No price for {ticker} (wrong ticker or not covered by Finnhub)")
    return Quote(
        symbol=ticker,
        price=float(price),
        open=float(data.get("o") or price),
        high=float(data.get("h") or price),
        low=float(data.get("l") or price),
        prev_close=float(data.get("pc") or 0),
        traded_at=datetime.fromtimestamp(int(ts), tz=timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )


def get_quotes(tickers: list[str]) -> tuple[dict[str, Quote], dict[str, str]]:
    """Fetch quotes sequentially under the rate limit. Returns (quotes, errors)."""
    quotes: dict[str, Quote] = {}
    errors: dict[str, str] = {}
    with httpx.Client() as client:
        for t in tickers:
            try:
                quotes[t] = get_quote(t, client)
            except QuoteError as e:
                errors[t] = str(e)
    return quotes, errors


@dataclass(frozen=True)
class MarketStatus:
    is_open: bool
    session: str        # "regular", "pre-market", "post-market" or "closed"
    holiday: str | None
    source: str


def market_status() -> MarketStatus:
    """US market status (knows holidays and early closes). Falls back to the clock on error."""
    try:
        data = _get("/stock/market-status", {"exchange": "US"})
        session = data.get("session") or ("regular" if data.get("isOpen") else "closed")
        return MarketStatus(
            is_open=bool(data.get("isOpen")) and session == "regular",
            session=session, holiday=data.get("holiday"), source="Finnhub",
        )
    except QuoteError as e:
        log.warning("market-status fallback to clock: %s", e)
        open_ = is_regular_hours_clock()
        return MarketStatus(is_open=open_, session="regular" if open_ else "closed", holiday=None, source="clock")
