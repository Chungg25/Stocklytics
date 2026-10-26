from datetime import date

import pandas as pd
import pytest

from conftest import make_ohlc
from stockbot.backtest.runner import BacktestError, parse_period, run_backtest
from stockbot.backtest.simulator import simulate_ticker
from stockbot.strategy.dsl import parse_strategy


def strat(entry_level, exit_level=None, **risk):
    s, e = parse_strategy({
        "name": "t", "universe": {"tickers": ["AAA"]},
        "entry": {"left": {"price": "close"}, "op": "crosses_above", "right": entry_level},
        **({"exit": {"left": {"price": "close"}, "op": "crosses_below", "right": exit_level}} if exit_level else {}),
        "risk": risk,
    })
    assert not e, e
    return s


def test_signal_on_close_fills_next_open_no_lookahead():
    closes = [10, 10, 12, 13, 14, 9, 9]
    opens = [10, 10, 11, 12.5, 13.5, 13, 9]
    df = make_ohlc(closes, opens=opens)
    r = simulate_ticker(strat(11, 10), "AAA", df, df.index[0], 1000, fee_bps=0, slippage_bps=0)
    t = r.trades[0]
    # Close crossed above 11 on bar 2 → bought at bar 3's OPEN (12.5), not bar 2's close (12).
    assert t.entry_date == df.index[3] and t.entry_price == 12.5
    # Close crossed below 10 on bar 5 → sold at bar 6's open (9).
    assert t.exit_date == df.index[6] and t.exit_price == 9 and t.exit_reason == "signal"


def test_stop_loss_and_gap_fill():
    closes = [10, 12, 12, 12, 8]
    opens = [10, 10, 12, 12, 8]       # gap down through the stop on the last bar
    lows = [10, 10, 11.5, 11.5, 7.5]
    df = make_ohlc(closes, opens=opens, lows=lows)
    r = simulate_ticker(strat(11, stop_loss_pct=10), "AAA", df, df.index[0], 1000, fee_bps=0, slippage_bps=0)
    t = r.trades[0]
    assert t.entry_price == 12 and t.exit_reason == "stop_loss"
    assert t.exit_price == 8  # filled at the gap open, not at the 10.8 stop level


def test_take_profit_intrabar():
    closes = [10, 12, 12.5, 13]
    opens = [10, 10, 12, 12.5]
    highs = [10, 12, 12.6, 14.0]
    df = make_ohlc(closes, opens=opens, highs=highs)
    r = simulate_ticker(strat(11, take_profit_pct=10), "AAA", df, df.index[0], 1000, fee_bps=0, slippage_bps=0)
    t = r.trades[0]
    assert t.exit_reason == "take_profit" and t.exit_price == pytest.approx(13.2)


def test_fees_reduce_returns():
    df = make_ohlc([10, 12, 13, 14, 9, 9], opens=[10, 10, 12.5, 13.5, 13, 9])
    free = simulate_ticker(strat(11, 10), "AAA", df, df.index[0], 1000, 0, 0)
    paid = simulate_ticker(strat(11, 10), "AAA", df, df.index[0], 1000, 10, 10)
    assert paid.equity.iloc[-1] < free.equity.iloc[-1]


def test_runner_portfolio_and_warnings():
    df = make_ohlc([10 + (i % 20) for i in range(300)], start="2023-01-02")
    loader = lambda tickers, s, e: {t: df for t in tickers}  # noqa: E731
    s, _ = parse_strategy({"name": "osc", "universe": {"tickers": ["AAA", "BBB"]},
                           "entry": {"left": {"price": "close"}, "op": "crosses_above", "right": 14},
                           "exit": {"left": {"price": "close"}, "op": "crosses_below", "right": 12}})
    res = run_backtest(s, date(2023, 3, 1), date(2024, 1, 31), loader=loader)
    out = res.to_dict(include_curve=True)
    assert out["portfolio"]["total_trades"] > 0
    assert set(out["per_ticker"]) == {"AAA", "BBB"}
    assert out["equity_curve"][-1]["date"] <= "2024-01-31"
    assert any("Past performance" in w for w in out["warnings"])


def test_runner_reports_missing_data():
    s = strat(11)
    with pytest.raises(BacktestError):
        run_backtest(s, date(2024, 1, 1), date(2024, 6, 1), loader=lambda t, a, b: {"AAA": pd.DataFrame()})


def test_parse_period():
    s, e = parse_period("1y")
    assert 360 <= (e - s).days <= 366
    with pytest.raises(BacktestError):
        parse_period("forever")
