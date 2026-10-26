"""Deterministic long-only backtest of a Strategy on daily bars.

Execution model (no look-ahead):
- Signals are computed on the close of bar t and filled at the OPEN of bar t+1.
- Stop-loss / trailing stop / take-profit are checked intrabar on t+1 onward using High/Low;
  a gap through the level fills at the open. If stop and target are both touched in the
  same bar, the stop is assumed to fill first (conservative).
- Fees and slippage are charged on both sides.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from stockbot.strategy import indicators
from stockbot.strategy.dsl import Strategy
from stockbot.strategy.engine import Evaluator


@dataclass
class Trade:
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str | None = None   # signal | stop_loss | trailing_stop | take_profit | end_of_data
    bars_held: int = 0
    shares: float = 0.0
    pnl: float = 0.0

    @property
    def return_pct(self) -> float:
        if self.exit_price is None:
            return 0.0
        return (self.exit_price / self.entry_price - 1) * 100

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "entry_date": self.entry_date.strftime("%Y-%m-%d"),
            "entry_price": round(float(self.entry_price), 4),
            "exit_date": self.exit_date.strftime("%Y-%m-%d") if self.exit_date is not None else None,
            "exit_price": round(float(self.exit_price), 4) if self.exit_price is not None else None,
            "exit_reason": self.exit_reason,
            "return_pct": round(float(self.return_pct), 2),
            "pnl": round(float(self.pnl), 2),
            "bars_held": int(self.bars_held),
        }


@dataclass
class TickerResult:
    ticker: str
    equity: pd.Series                       # mark-to-market equity at each close
    buy_hold: pd.Series                     # same capital simply bought at the first close
    in_market: pd.Series                    # bool per bar
    trades: list[Trade] = field(default_factory=list)


def stop_levels(strategy: Strategy, entry_price: float, atr_value: float | None) -> tuple[float | None, float | None]:
    r = strategy.risk
    stops = []
    if r.stop_loss_pct:
        stops.append(entry_price * (1 - r.stop_loss_pct / 100))
    if r.atr_stop_mult and atr_value and atr_value == atr_value:
        stops.append(entry_price - r.atr_stop_mult * atr_value)
    stop = max(stops) if stops else None
    target = entry_price * (1 + r.take_profit_pct / 100) if r.take_profit_pct else None
    return stop, target


def simulate_ticker(
    strategy: Strategy,
    ticker: str,
    df: pd.DataFrame,
    start: pd.Timestamp,
    capital: float,
    fee_bps: float = 5.0,
    slippage_bps: float = 5.0,
) -> TickerResult:
    """`df` must include warm-up bars before `start`; trading only happens from `start`."""
    ev = Evaluator(df)
    entry_sig = ev.condition(strategy.entry).to_numpy()
    exit_sig = ev.condition(strategy.exit).to_numpy() if strategy.exit is not None else np.zeros(len(df), bool)
    atr14 = indicators.atr(df, 14).to_numpy() if strategy.risk.atr_stop_mult else None

    o, h, lo, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    dates = df.index
    first = int(np.searchsorted(dates.values, np.datetime64(start)))
    fee, slip = fee_bps / 1e4, slippage_bps / 1e4
    trail_pct = strategy.risk.trailing_stop_pct

    cash, shares = capital, 0.0
    trade: Trade | None = None
    stop = target = None
    peak = 0.0
    pending_entry = pending_exit = False
    trades: list[Trade] = []
    equity, in_mkt = [], []

    def close_trade(i: int, raw_price: float, reason: str) -> None:
        nonlocal cash, shares, trade, stop, target
        fill = raw_price * (1 - slip)
        proceeds = shares * fill * (1 - fee)
        assert trade is not None
        trade.exit_date, trade.exit_price, trade.exit_reason = dates[i], fill, reason
        trade.bars_held = i - dates.get_loc(trade.entry_date)
        trade.pnl = proceeds - trade.shares * trade.entry_price * (1 + fee)
        trades.append(trade)
        cash += proceeds
        shares, trade, stop, target = 0.0, None, None, None

    for i in range(first, len(df)):
        # 1) Orders decided at the previous close fill at today's open.
        if pending_exit and trade is not None:
            close_trade(i, o[i], "signal")
        elif pending_entry and trade is None and cash > 0:
            fill = o[i] * (1 + slip)
            shares = cash * (1 - fee) / fill
            trade = Trade(ticker, dates[i], fill, shares=shares)
            cash = 0.0
            stop, target = stop_levels(strategy, fill, atr14[i - 1] if atr14 is not None and i > 0 else None)
            peak = fill
        pending_entry = pending_exit = False

        # 2) Intrabar risk exits.
        if trade is not None:
            eff_stop, reason = stop, "stop_loss"
            if trail_pct:
                trail = peak * (1 - trail_pct / 100)
                if eff_stop is None or trail > eff_stop:
                    eff_stop, reason = trail, "trailing_stop"
            if eff_stop is not None and lo[i] <= eff_stop:
                close_trade(i, min(o[i], eff_stop), reason)
            elif target is not None and h[i] >= target:
                close_trade(i, max(o[i], target), "take_profit")
            else:
                peak = max(peak, h[i])

        # 3) Decide at today's close.
        if trade is None:
            pending_entry = bool(entry_sig[i])
        else:
            pending_exit = bool(exit_sig[i])

        equity.append(cash + shares * c[i])
        in_mkt.append(trade is not None)

    idx = dates[first:]
    if trade is not None and len(idx):
        # Mark the open position at the last close so metrics include it.
        last = len(df) - 1
        trade.exit_date, trade.exit_price, trade.exit_reason = dates[last], c[last], "end_of_data"
        trade.bars_held = last - dates.get_loc(trade.entry_date)
        trade.pnl = shares * c[last] - trade.shares * trade.entry_price * (1 + fee)
        trades.append(trade)

    eq = pd.Series(equity, index=idx, dtype=float)
    bh = capital * c[first:] / c[first] if len(idx) else np.array([])
    return TickerResult(ticker, eq, pd.Series(bh, index=idx, dtype=float),
                        pd.Series(in_mkt, index=idx, dtype=bool), trades)
