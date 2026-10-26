import numpy as np
import pandas as pd

from conftest import make_ohlc
from stockbot.strategy import indicators
from stockbot.strategy.describe import describe
from stockbot.strategy.dsl import Comparison, IndicatorRef, PriceRef, parse_strategy, warmup_bars
from stockbot.strategy.engine import evaluate, explain_at

BASE = {"name": "t", "universe": {"tickers": ["AAA"]}}


def test_valid_strategy_and_description():
    s, errors = parse_strategy({
        **BASE,
        "universe": {"tickers": ["aapl", "AAPL", "brk.b"]},
        "entry": {"all": [
            {"left": {"ind": "rsi", "period": 14}, "op": "crosses_above", "right": 30},
            {"left": {"price": "close"}, "op": ">", "right": {"ind": "sma", "period": 200}},
        ]},
        "exit": {"left": {"ind": "rsi"}, "op": ">", "right": 70},
        "risk": {"stop_loss_pct": 7},
    })
    assert errors == []
    assert s.universe.resolve() == ["AAPL", "BRK.B"]
    text = describe(s)
    assert "RSI(14) crosses above 30 AND price is above 200-day MA" in text
    assert "stop-loss 7%" in text
    assert warmup_bars(s) >= 200


def test_invalid_strategies_give_readable_errors():
    _, e = parse_strategy({**BASE, "entry": {"left": 1, "op": ">", "right": 2}})
    assert any("Cannot compare two numbers" in m for m in e)
    _, e = parse_strategy({**BASE, "entry": {"left": {"ind": "macd", "period": 3}, "op": ">", "right": 0}})
    assert e == ["entry.left: MACD uses fast/slow/signal, not period"]
    _, e = parse_strategy({**BASE, "entry": {"left": {"price": "close"}, "op": ">", "right": 1}, "code": "import os"})
    assert any("Extra inputs" in m for m in e)
    _, e = parse_strategy({**BASE, "universe": {"tickers": ["rm -rf"]}, "entry": {"left": {"price": "close"}, "op": ">", "right": 1}})
    assert any("Invalid ticker" in m for m in e)


def test_sma_and_rsi_reference_values():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert indicators.sma(s, 3).tolist()[2:] == [2.0, 3.0, 4.0]
    up = pd.Series(np.arange(1, 40, dtype=float))
    assert indicators.rsi(up, 14).iloc[-1] == 100.0
    down = pd.Series(np.arange(40, 1, -1, dtype=float))
    assert indicators.rsi(down, 14).iloc[-1] == 0.0
    rng = np.random.default_rng(0)
    r = indicators.rsi(pd.Series(100 + rng.normal(0, 1, 300).cumsum()), 14).dropna()
    assert r.between(0, 100).all()


def test_crosses_above_fires_only_on_the_crossing_bar():
    df = make_ohlc([10, 9, 8, 12, 13, 14, 9, 15])
    cond = Comparison(left=PriceRef(price="close"), op="crosses_above", right=11.0)
    assert evaluate(df, cond).tolist() == [False, False, False, True, False, False, False, True]


def test_highest_excludes_current_bar_for_breakouts():
    df = make_ohlc([10, 11, 12, 11, 13])
    cond = Comparison(left=PriceRef(price="close"), op=">", right=IndicatorRef(ind="highest", period=3))
    assert evaluate(df, cond).tolist() == [False, False, False, False, True]


def test_explain_reports_values():
    df = make_ohlc([10, 9, 8, 12])
    cond = Comparison(left=PriceRef(price="close"), op=">", right=11.0)
    row = explain_at(df, cond)[0]
    assert row["passed"] is True and row["left_value"] == 12.0 and row["right_value"] == 11.0
