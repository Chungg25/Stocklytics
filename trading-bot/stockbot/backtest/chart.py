"""PNG charts sent to Telegram (backtest result and alert snapshot)."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from stockbot.backtest.runner import BacktestResult  # noqa: E402

_GREEN, _RED, _BLUE, _GREY = "#16a34a", "#dc2626", "#2563eb", "#9ca3af"


def _to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def backtest_chart(result: BacktestResult) -> bytes:
    eq, bh = result.equity, result.buy_hold
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(eq.index, eq.values, color=_BLUE, lw=1.8, label=f"Strategy ({result.portfolio['total_return_pct']:+.1f}%)")
    ax1.plot(bh.index, bh.values, color=_GREY, lw=1.2, ls="--", label=f"Buy & hold ({result.portfolio['buy_hold_return_pct']:+.1f}%)")
    if len(result.ticker_results) == 1:
        tr = next(iter(result.ticker_results.values()))
        for t in tr.trades:
            if t.entry_date in eq.index:
                ax1.scatter(t.entry_date, eq.loc[t.entry_date], marker="^", color=_GREEN, s=28, zorder=3)
            if t.exit_date is not None and t.exit_date in eq.index and t.exit_reason != "end_of_data":
                ax1.scatter(t.exit_date, eq.loc[t.exit_date], marker="v", color=_RED, s=28, zorder=3)
    ax1.set_title(f"{result.strategy.name} — {result.start:%b %d, %Y} → {result.end:%b %d, %Y}", fontsize=11)
    ax1.set_ylabel("Portfolio value ($)")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.25)

    dd = (eq / eq.cummax() - 1) * 100
    ax2.fill_between(dd.index, dd.values, 0, color=_RED, alpha=0.3)
    ax2.set_ylabel("Drawdown %")
    ax2.grid(alpha=0.25)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return _to_png(fig)


def alert_chart(df: pd.DataFrame, ticker: str, price: float, stop: float | None, target: float | None,
                overlays: dict[str, pd.Series] | None = None, bars: int = 120) -> bytes:
    view = df.tail(bars)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(view.index, view["Close"], color=_BLUE, lw=1.5, label="Close")
    for name, series in (overlays or {}).items():
        s = series.reindex(view.index)
        if s.notna().any():
            ax.plot(s.index, s.values, lw=1, alpha=0.8, label=name)
    ax.axhline(price, color="black", lw=0.8, ls=":", label=f"Now {price:,.2f}")
    if stop:
        ax.axhline(stop, color=_RED, lw=1, ls="--", label=f"Stop {stop:,.2f}")
    if target:
        ax.axhline(target, color=_GREEN, lw=1, ls="--", label=f"Target {target:,.2f}")
    ax.set_title(ticker, fontsize=11)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()
    return _to_png(fig)
