"""High-level backtest entry point: fetch data, simulate every ticker, aggregate, explain."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

import pandas as pd

from stockbot.backtest.metrics import summarize
from stockbot.backtest.simulator import TickerResult, simulate_ticker
from stockbot.data.history import get_daily
from stockbot.data.market import now_et
from stockbot.strategy.dsl import Strategy, warmup_bars

DataLoader = Callable[[list[str], date, date], dict[str, pd.DataFrame]]

_PERIOD_RE = re.compile(r"^\s*(\d{1,2})\s*([ymd])\s*$", re.I)
MAX_YEARS = 20


class BacktestError(ValueError):
    pass


def parse_period(period: str | None, start: str | None = None, end: str | None = None) -> tuple[date, date]:
    """'3y', '6m', '90d' or explicit ISO start/end. Default: 3 years up to the last completed session."""
    today = now_et().date()
    if start:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end) if end else today
    else:
        m = _PERIOD_RE.match(period or "3y")
        if not m:
            raise BacktestError("Invalid period. Examples: 1y, 3y, 5y, 6m")
        n, unit = int(m.group(1)), m.group(2).lower()
        days = {"y": 365 * n, "m": 30 * n, "d": n}[unit]
        e, s = today, today - timedelta(days=days)
    if s >= e:
        raise BacktestError("Start date must be before end date")
    if (e - s).days > 365 * MAX_YEARS:
        raise BacktestError(f"At most {MAX_YEARS} years")
    if (e - s).days < 60:
        raise BacktestError("Period too short — use at least about 2 months")
    return s, e


@dataclass
class BacktestResult:
    strategy: Strategy
    start: date
    end: date
    capital: float
    portfolio: dict
    per_ticker: dict[str, dict]
    trades: list[dict]
    equity: pd.Series
    buy_hold: pd.Series
    warnings: list[str]
    skipped: dict[str, str]
    ticker_results: dict[str, TickerResult]

    def to_dict(self, include_curve: bool = False) -> dict:
        out = {
            "strategy": self.strategy.name,
            "period": {"start": self.start.isoformat(), "end": self.end.isoformat()},
            "initial_capital": self.capital,
            "portfolio": self.portfolio,
            "per_ticker": self.per_ticker,
            "recent_trades": self.trades[-15:],
            "total_trades_listed": len(self.trades),
            "warnings": self.warnings,
            "skipped_tickers": self.skipped,
            "assumptions": [
                "Signals use the daily close; trades fill at the next session's open",
                "Prices adjusted for splits and dividends (Yahoo Finance)",
                "0.05% fee + 0.05% slippage on each side",
                "Capital split equally across tickers, one long position per ticker at a time",
            ],
        }
        if include_curve:
            out["equity_curve"] = [
                {"date": d.strftime("%Y-%m-%d"), "equity": round(float(v), 2), "buy_hold": round(float(b), 2)}
                for d, v, b in zip(self.equity.index, self.equity.values, self.buy_hold.values, strict=True)
            ]
        return out


def _warnings(strategy: Strategy, pf: dict) -> list[str]:
    w = []
    if pf["total_trades"] == 0:
        w.append("No trades in this period — the conditions may be too strict.")
    elif pf["total_trades"] < 10:
        w.append(f"Only {pf['total_trades']} trades — too few to be statistically reliable.")
    if pf["total_trades"] and pf["total_return_pct"] < pf["buy_hold_return_pct"]:
        w.append("The strategy underperformed simply buying and holding over the same period.")
    if pf["max_drawdown_pct"] < -30:
        w.append(f"Max drawdown {pf['max_drawdown_pct']}% — high risk.")
    if not strategy.has_exit_rule():
        w.append("No sell rule or stop-loss.")
    w.append("Past performance does not guarantee future results.")
    return w


def run_backtest(
    strategy: Strategy,
    start: date,
    end: date,
    capital: float = 10_000.0,
    loader: DataLoader | None = None,
    fee_bps: float = 5.0,
    slippage_bps: float = 5.0,
) -> BacktestResult:
    loader = loader or get_daily
    tickers = strategy.universe.resolve()
    warm_days = int(warmup_bars(strategy) * 1.5) + 10
    data = loader(tickers, start - timedelta(days=warm_days), end)

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    usable: dict[str, pd.DataFrame] = {}
    skipped: dict[str, str] = {}
    for t in tickers:
        df = data.get(t)
        if df is not None and not df.empty:
            df = df[df.index <= end_ts]
        if df is None or df.empty:
            skipped[t] = "no data"
        elif (df.index >= start_ts).sum() < 20:
            skipped[t] = "not enough data in the period (recently listed?)"
        else:
            usable[t] = df
    if not usable:
        raise BacktestError("Could not load data for any ticker: " + ", ".join(f"{k} ({v})" for k, v in skipped.items()))

    alloc = capital / len(usable)
    results = {t: simulate_ticker(strategy, t, df, start_ts, alloc, fee_bps, slippage_bps) for t, df in usable.items()}

    # Portfolio = sum of per-ticker sleeves; before a ticker's first bar its sleeve is idle cash.
    idx = sorted(set().union(*(r.equity.index for r in results.values())))
    equity = sum(r.equity.reindex(idx).ffill().fillna(alloc) for r in results.values())
    buy_hold = sum(r.buy_hold.reindex(idx).ffill().fillna(alloc) for r in results.values())
    in_market = pd.concat([r.in_market.reindex(idx).fillna(False) for r in results.values()], axis=1).any(axis=1)
    all_trades = sorted((tr for r in results.values() for tr in r.trades), key=lambda tr: tr.entry_date)

    portfolio = summarize(equity, buy_hold, in_market, all_trades)
    per_ticker = {t: summarize(r.equity, r.buy_hold, r.in_market, r.trades) for t, r in results.items()}

    return BacktestResult(
        strategy=strategy, start=start, end=end, capital=capital,
        portfolio=portfolio, per_ticker=per_ticker, trades=[tr.to_dict() for tr in all_trades],
        equity=equity, buy_hold=buy_hold, warnings=_warnings(strategy, portfolio),
        skipped=skipped, ticker_results=results,
    )
