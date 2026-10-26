"""Vectorized evaluation of DSL conditions over OHLCV data.

The same functions are used by the backtester and the live alert engine, so a live
alert fires exactly when the backtest would have taken the trade.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from stockbot.strategy import indicators
from stockbot.strategy.dsl import AllOf, AnyOf, Comparison, IndicatorRef, Not, PriceRef

_PRICE_COL = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}


class Evaluator:
    """Caches indicator series for one DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._cache: dict[str, pd.Series] = {}

    def operand(self, op: Any) -> pd.Series:
        if isinstance(op, (int, float)):
            return pd.Series(float(op), index=self.df.index)
        key = op.model_dump_json()
        if key not in self._cache:
            if isinstance(op, PriceRef):
                s = self.df[_PRICE_COL[op.price]].astype(float)
                self._cache[key] = s.shift(op.shift) if op.shift else s
            elif isinstance(op, IndicatorRef):
                self._cache[key] = indicators.compute(self.df, op)
            else:  # pragma: no cover
                raise TypeError(f"Unsupported operand {op!r}")
        return self._cache[key]

    def condition(self, cond: Any) -> pd.Series:
        if isinstance(cond, Comparison):
            left, right = self.operand(cond.left), self.operand(cond.right)
            valid = left.notna() & right.notna()
            if cond.op == ">":
                res = left > right
            elif cond.op == "<":
                res = left < right
            elif cond.op == ">=":
                res = left >= right
            elif cond.op == "<=":
                res = left <= right
            else:
                pl, pr = left.shift(1), right.shift(1)
                valid &= pl.notna() & pr.notna()
                if cond.op == "crosses_above":
                    res = (left > right) & (pl <= pr)
                else:
                    res = (left < right) & (pl >= pr)
            return (res & valid).astype(bool)
        if isinstance(cond, AllOf):
            out = pd.Series(True, index=self.df.index)
            for c in cond.all:
                out &= self.condition(c)
            return out
        if isinstance(cond, AnyOf):
            out = pd.Series(False, index=self.df.index)
            for c in cond.any:
                out |= self.condition(c)
            return out
        if isinstance(cond, Not):
            return ~self.condition(cond.not_)
        raise TypeError(f"Unsupported condition {cond!r}")  # pragma: no cover


def evaluate(df: pd.DataFrame, cond: Any) -> pd.Series:
    return Evaluator(df).condition(cond)


def explain_at(df: pd.DataFrame, cond: Any, idx: int = -1) -> list[dict]:
    """Values of every comparison at bar `idx` — used to show *why* an alert fired."""
    ev = Evaluator(df)
    rows: list[dict] = []

    def walk(c: Any) -> None:
        if isinstance(c, Comparison):
            left, right = ev.operand(c.left), ev.operand(c.right)
            rows.append({
                "left": c.left, "op": c.op, "right": c.right,
                "left_value": _num(left.iloc[idx]), "right_value": _num(right.iloc[idx]),
                "passed": bool(ev.condition(c).iloc[idx]),
            })
            return
        children = c.all if isinstance(c, AllOf) else c.any if isinstance(c, AnyOf) else [c.not_]
        for child in children:
            walk(child)

    walk(cond)
    return rows


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else round(f, 4)
