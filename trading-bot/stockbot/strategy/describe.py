"""Plain-English rendering of a strategy, so non-technical users can confirm it."""
from __future__ import annotations

from typing import Any

from stockbot.strategy.dsl import AllOf, Comparison, IndicatorRef, Not, PriceRef, Strategy

_PRICE_EN = {"open": "open", "high": "high", "low": "low", "close": "price", "volume": "volume"}
_OP_EN = {">": "is above", "<": "is below", ">=": "is at or above", "<=": "is at or below",
          "crosses_above": "crosses above", "crosses_below": "crosses below"}


def operand_text(op: Any) -> str:
    if isinstance(op, (int, float)):
        return f"{op:g}"
    if isinstance(op, PriceRef):
        base = _PRICE_EN[op.price]
        return f"{base} {op.shift} day(s) ago" if op.shift else base
    assert isinstance(op, IndicatorRef)
    n = op.resolved_period()
    src = "" if op.source == "close" else f" of {_PRICE_EN[op.source]}"
    name = op.ind
    if name == "sma":
        text = f"{n}-day MA{src}"
    elif name == "ema":
        text = f"{n}-day EMA{src}"
    elif name == "rsi":
        text = f"RSI({n})"
    elif name.startswith("macd"):
        params = f"({op.fast or 12},{op.slow or 26},{op.signal or 9})"
        text = {"macd": f"MACD{params}", "macd_signal": f"MACD signal line{params}",
                "macd_hist": f"MACD histogram{params}"}[name]
    elif name.startswith("bb_"):
        k = op.std or 2
        text = {"bb_upper": "upper", "bb_middle": "middle", "bb_lower": "lower",
                "bb_width": "width (%) of"}[name] + f" Bollinger Band({n},{k:g})"
    elif name == "atr":
        text = f"ATR({n})"
    elif name == "stoch_k":
        text = f"Stochastic %K({n})"
    elif name == "stoch_d":
        text = f"Stochastic %D({n},{op.smooth or 3})"
    elif name == "adx":
        text = f"ADX({n})"
    elif name == "obv":
        text = "OBV"
    elif name == "volume_sma":
        text = f"{n}-day average volume"
    elif name == "pct_change":
        text = f"{n}-day % change{src}"
    elif name == "highest":
        text = f"highest high of the prior {n} days"
    elif name == "lowest":
        text = f"lowest low of the prior {n} days"
    else:
        text = name
    return f"{text} ({op.shift} day(s) ago)" if op.shift else text


def condition_text(cond: Any, depth: int = 0) -> str:
    if isinstance(cond, Comparison):
        return f"{operand_text(cond.left)} {_OP_EN[cond.op]} {operand_text(cond.right)}"
    if isinstance(cond, Not):
        return f"NOT ({condition_text(cond.not_, depth + 1)})"
    parts = cond.all if isinstance(cond, AllOf) else cond.any
    joiner = " AND " if isinstance(cond, AllOf) else " OR "
    text = joiner.join(condition_text(c, depth + 1) for c in parts)
    return f"({text})" if depth and len(parts) > 1 else text


def risk_text(strategy: Strategy) -> str:
    r = strategy.risk
    parts = []
    if r.stop_loss_pct:
        parts.append(f"stop-loss {r.stop_loss_pct:g}%")
    if r.atr_stop_mult:
        parts.append(f"stop-loss {r.atr_stop_mult:g}× ATR(14)")
    if r.trailing_stop_pct:
        parts.append(f"trailing stop {r.trailing_stop_pct:g}% from peak")
    if r.take_profit_pct:
        parts.append(f"take-profit {r.take_profit_pct:g}%")
    return ", ".join(parts)


def describe(strategy: Strategy) -> str:
    tickers = ", ".join(strategy.universe.resolve())
    lines = [
        f"📌 {strategy.name}",
        f"• Watching: {tickers}",
        "• Timeframe: daily candles",
        f"• BUY when: {condition_text(strategy.entry)}",
    ]
    if strategy.exit is not None:
        lines.append(f"• SELL when: {condition_text(strategy.exit)}")
    risk = risk_text(strategy)
    if risk:
        lines.append(f"• Risk: {risk}")
    if not strategy.has_exit_rule():
        lines.append("⚠️ No sell rule or stop-loss — positions are held until the end of the test period.")
    return "\n".join(lines)
