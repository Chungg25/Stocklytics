"""Technical indicators implemented with pandas only (standard textbook definitions).

All functions take an OHLCV DataFrame with columns Open, High, Low, Close, Volume
and return a Series aligned to its index.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stockbot.strategy.dsl import IndicatorRef

_SOURCE_COL = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    out = s.ewm(span=n, adjust=False, min_periods=n).mean()
    return out


def _wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    gain = _wilder(delta.clip(lower=0), n)
    loss = _wilder(-delta.clip(upper=0), n)
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    # No losses in the window -> RSI 100; flat window -> 50.
    out = out.where(loss != 0, np.where(gain > 0, 100.0, 50.0))
    return out.where(gain.notna())


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["Close"].shift(1)
    return pd.concat(
        [df["High"] - df["Low"], (df["High"] - prev_close).abs(), (df["Low"] - prev_close).abs()], axis=1
    ).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return _wilder(true_range(df), n)


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
    line = line.where(s.expanding().count() >= slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, sig, line - sig


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(s, n)
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return mid + k * sd, mid, mid - k * sd


def stochastic(df: pd.DataFrame, n: int = 14, smooth: int = 3) -> tuple[pd.Series, pd.Series]:
    lo = df["Low"].rolling(n, min_periods=n).min()
    hi = df["High"].rolling(n, min_periods=n).max()
    rng = (hi - lo).replace(0, np.nan)
    k = 100 * (df["Close"] - lo) / rng
    return k, sma(k, smooth)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["High"].diff()
    down = -df["Low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = _wilder(true_range(df), n)
    plus_di = 100 * _wilder(plus_dm, n) / tr
    minus_di = 100 * _wilder(minus_dm, n) / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _wilder(dx, n)


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["Close"].diff()).fillna(0)
    return (direction * df["Volume"]).cumsum()


def compute(df: pd.DataFrame, ref: IndicatorRef) -> pd.Series:
    """Evaluate an IndicatorRef on df."""
    src = df[_SOURCE_COL[ref.source]].astype(float)
    n = ref.resolved_period()
    name = ref.ind
    if name == "sma":
        out = sma(src, n)
    elif name == "ema":
        out = ema(src, n)
    elif name == "rsi":
        out = rsi(src, n)
    elif name.startswith("macd"):
        line, sig, hist = macd(src, ref.fast or 12, ref.slow or 26, ref.signal or 9)
        out = {"macd": line, "macd_signal": sig, "macd_hist": hist}[name]
    elif name.startswith("bb_"):
        upper, mid, lower = bollinger(src, n, ref.std or 2.0)
        out = {"bb_upper": upper, "bb_middle": mid, "bb_lower": lower,
               "bb_width": (upper - lower) / mid * 100}[name]
    elif name == "atr":
        out = atr(df, n)
    elif name in ("stoch_k", "stoch_d"):
        k, d = stochastic(df, n, ref.smooth or 3)
        out = k if name == "stoch_k" else d
    elif name == "adx":
        out = adx(df, n)
    elif name == "obv":
        out = obv(df)
    elif name == "volume_sma":
        out = sma(df["Volume"].astype(float), n)
    elif name == "pct_change":
        out = src.pct_change(n) * 100
    elif name == "highest":
        # Highest high of the previous n bars (excludes the current bar) -> "close > highest(20)" is a breakout.
        col = df["High"] if ref.source == "close" else src
        out = col.shift(1).rolling(n, min_periods=n).max()
    elif name == "lowest":
        col = df["Low"] if ref.source == "close" else src
        out = col.shift(1).rolling(n, min_periods=n).min()
    else:  # pragma: no cover - guarded by the DSL Literal
        raise ValueError(f"Unknown indicator {name}")
    return out.shift(ref.shift) if ref.shift else out
