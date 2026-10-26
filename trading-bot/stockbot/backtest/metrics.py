"""Performance statistics for equity curves and trade lists."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from stockbot.backtest.simulator import Trade

TRADING_DAYS = 252


def max_drawdown_pct(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    dd = equity / equity.cummax() - 1
    return float(dd.min() * 100)


def cagr_pct(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    ratio = equity.iloc[-1] / equity.iloc[0]
    return float((ratio ** (1 / years) - 1) * 100) if ratio > 0 else -100.0


def sharpe(equity: pd.Series) -> float:
    rets = equity.pct_change().dropna()
    if len(rets) < 2 or rets.std(ddof=1) == 0:
        return 0.0
    return float(rets.mean() / rets.std(ddof=1) * math.sqrt(TRADING_DAYS))


def summarize(equity: pd.Series, buy_hold: pd.Series, in_market: pd.Series, trades: list[Trade]) -> dict:
    start_val = float(equity.iloc[0]) if len(equity) else 0.0
    end_val = float(equity.iloc[-1]) if len(equity) else 0.0
    rets = np.array([t.return_pct for t in trades])
    wins, losses = rets[rets > 0], rets[rets <= 0]
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    pf = gross_win / gross_loss if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    bh_ret = (buy_hold.iloc[-1] / buy_hold.iloc[0] - 1) * 100 if len(buy_hold) else 0.0
    return {
        "start_value": round(start_val, 2),
        "end_value": round(end_val, 2),
        "total_return_pct": round((end_val / start_val - 1) * 100, 2) if start_val else 0.0,
        "buy_hold_return_pct": round(float(bh_ret), 2),
        "cagr_pct": round(cagr_pct(equity), 2),
        "max_drawdown_pct": round(max_drawdown_pct(equity), 2),
        "buy_hold_max_drawdown_pct": round(max_drawdown_pct(buy_hold), 2),
        "sharpe": round(sharpe(equity), 2),
        "total_trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "avg_trade_pct": round(float(rets.mean()), 2) if trades else 0.0,
        "avg_win_pct": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss_pct": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "best_trade_pct": round(float(rets.max()), 2) if trades else 0.0,
        "worst_trade_pct": round(float(rets.min()), 2) if trades else 0.0,
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "avg_bars_held": round(float(np.mean([t.bars_held for t in trades])), 1) if trades else 0.0,
        "exposure_pct": round(float(in_market.mean() * 100), 1) if len(in_market) else 0.0,
    }
