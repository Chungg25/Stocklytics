"""Daily OHLCV history (split/dividend adjusted) from Yahoo Finance via yfinance.

Only *completed* daily bars are returned: if today's session is still running, the
partial row Yahoo returns for today is dropped. The live alert engine appends its own
bar built from a timestamped Finnhub quote instead.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from stockbot.data.market import REGULAR_CLOSE, now_et

log = logging.getLogger(__name__)

_COLS = ["Open", "High", "Low", "Close", "Volume"]
_CACHE_TTL_SECONDS = 6 * 3600
_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_lock = threading.Lock()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=_COLS)
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if c[0] in _COLS else c[-1] for c in df.columns]
    df = df[[c for c in _COLS if c in df.columns]]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[(df["Close"] > 0) & (df["High"] >= df["Low"])]
    return df.astype(float)


def _drop_unfinished_today(df: pd.DataFrame) -> pd.DataFrame:
    now = now_et()
    today = pd.Timestamp(now.date())
    finished = now.time() >= (datetime.combine(now.date(), REGULAR_CLOSE) + timedelta(minutes=20)).time()
    if not finished and len(df) and df.index[-1] >= today:
        return df[df.index < today]
    return df


def _download(tickers: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    raw = yf.download(
        tickers, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
        interval="1d", auto_adjust=True, group_by="ticker", progress=False, threads=True,
    )
    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            part = raw[t] if isinstance(raw.columns, pd.MultiIndex) and t in raw.columns.get_level_values(0) else raw
        except KeyError:
            part = pd.DataFrame()
        out[t] = _normalize(part)
    return out


def get_daily(tickers: list[str], start: date, end: date | None = None) -> dict[str, pd.DataFrame]:
    """Completed daily bars for each ticker in [start, end]. Missing tickers map to empty frames."""
    end = end or now_et().date()
    result: dict[str, pd.DataFrame] = {}
    to_fetch: list[str] = []
    now = time.time()
    with _lock:
        for t in tickers:
            hit = _cache.get(t)
            if hit and now - hit[0] < _CACHE_TTL_SECONDS and len(hit[1]) and hit[1].index[0] <= pd.Timestamp(start) + pd.Timedelta(days=7):
                result[t] = hit[1]
            else:
                to_fetch.append(t)
    if to_fetch:
        # Fetch a little earlier than asked so later requests with a longer warm-up hit the cache.
        fetched = _download(to_fetch, min(start, end - timedelta(days=365 * 6)), now_et().date())
        with _lock:
            for t, df in fetched.items():
                df = _drop_unfinished_today(df)
                _cache[t] = (now, df)
                result[t] = df
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    return {t: df[(df.index >= s) & (df.index <= e)] for t, df in result.items()}


def invalidate(tickers: list[str] | None = None) -> None:
    with _lock:
        if tickers is None:
            _cache.clear()
        else:
            for t in tickers:
                _cache.pop(t, None)
