"""Strategy DSL: a small, whitelisted JSON language for describing trading rules.

The LLM translates the user's natural-language idea into this structure; everything
after that (backtest, live checks) is deterministic code. No user or LLM code is executed.
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, ValidationError, field_validator, model_validator

MAX_DEPTH = 4
MAX_CONDITIONS = 12
MAX_TICKERS = 30
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")

IndicatorName = Literal[
    "sma", "ema", "rsi",
    "macd", "macd_signal", "macd_hist",
    "bb_upper", "bb_middle", "bb_lower", "bb_width",
    "atr", "stoch_k", "stoch_d", "adx", "obv",
    "volume_sma", "pct_change", "highest", "lowest",
]
PriceField = Literal["open", "high", "low", "close", "volume"]
Operator = Literal[">", "<", ">=", "<=", "crosses_above", "crosses_below"]

# Indicators that take a single `period` argument, and its default.
DEFAULT_PERIODS: dict[str, int] = {
    "sma": 20, "ema": 20, "rsi": 14, "atr": 14, "adx": 14,
    "bb_upper": 20, "bb_middle": 20, "bb_lower": 20, "bb_width": 20,
    "stoch_k": 14, "stoch_d": 14, "volume_sma": 20,
    "pct_change": 1, "highest": 20, "lowest": 20,
}

PRESETS: dict[str, list[str]] = {
    "mega_caps": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "BRK-B", "JPM"],
    "semiconductors": ["NVDA", "AMD", "AVGO", "TSM", "QCOM", "MU", "INTC", "AMAT", "LRCX", "ASML"],
    "index_etfs": ["SPY", "QQQ", "DIA", "IWM"],
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PriceRef(_Strict):
    price: PriceField
    shift: int = Field(0, ge=0, le=60, description="Value N bars ago (0 = current bar)")


class IndicatorRef(_Strict):
    ind: IndicatorName
    period: Optional[int] = Field(None, ge=1, le=400)
    source: PriceField = "close"
    # MACD
    fast: Optional[int] = Field(None, ge=2, le=100)
    slow: Optional[int] = Field(None, ge=3, le=300)
    signal: Optional[int] = Field(None, ge=2, le=100)
    # Bollinger
    std: Optional[float] = Field(None, gt=0, le=5)
    # Stochastic %D smoothing
    smooth: Optional[int] = Field(None, ge=1, le=20)
    shift: int = Field(0, ge=0, le=60)

    @model_validator(mode="after")
    def _check_params(self) -> "IndicatorRef":
        is_macd = self.ind.startswith("macd")
        if not is_macd and any(v is not None for v in (self.fast, self.slow, self.signal)):
            raise ValueError("fast/slow/signal only apply to macd, macd_signal, macd_hist")
        if is_macd and self.period is not None:
            raise ValueError("MACD uses fast/slow/signal, not period")
        if is_macd and (self.fast or 12) >= (self.slow or 26):
            raise ValueError("MACD: fast must be smaller than slow")
        if self.std is not None and not self.ind.startswith("bb_"):
            raise ValueError("std only applies to Bollinger (bb_*)")
        if self.smooth is not None and self.ind != "stoch_d":
            raise ValueError("smooth only applies to stoch_d")
        return self

    def resolved_period(self) -> int:
        return self.period or DEFAULT_PERIODS.get(self.ind, 14)


def _operand_kind(v: Any) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return "number"
    if isinstance(v, dict):
        return "price" if "price" in v else "indicator"
    if isinstance(v, PriceRef):
        return "price"
    if isinstance(v, IndicatorRef):
        return "indicator"
    return "number"


Operand = Annotated[
    Union[Annotated[float, Tag("number")], Annotated[PriceRef, Tag("price")], Annotated[IndicatorRef, Tag("indicator")]],
    Discriminator(_operand_kind),
]


class Comparison(_Strict):
    left: Operand
    op: Operator
    right: Operand

    @model_validator(mode="after")
    def _not_two_numbers(self) -> "Comparison":
        if isinstance(self.left, (int, float)) and isinstance(self.right, (int, float)):
            raise ValueError("Cannot compare two numbers; at least one side must be a price or an indicator")
        return self


class AllOf(_Strict):
    all: list["Condition"] = Field(min_length=1)


class AnyOf(_Strict):
    any: list["Condition"] = Field(min_length=1)


class Not(_Strict):
    not_: "Condition" = Field(alias="not")


def _condition_kind(v: Any) -> str:
    if isinstance(v, dict):
        for key in ("all", "any", "not"):
            if key in v:
                return key
        return "compare"
    return {AllOf: "all", AnyOf: "any", Not: "not"}.get(type(v), "compare")


Condition = Annotated[
    Union[Annotated[Comparison, Tag("compare")], Annotated[AllOf, Tag("all")],
          Annotated[AnyOf, Tag("any")], Annotated[Not, Tag("not")]],
    Discriminator(_condition_kind),
]
AllOf.model_rebuild()
AnyOf.model_rebuild()
Not.model_rebuild()


class Universe(_Strict):
    tickers: list[str] = Field(default_factory=list)
    preset: Optional[Literal["mega_caps", "semiconductors", "index_etfs"]] = None

    @field_validator("tickers")
    @classmethod
    def _norm_tickers(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for t in v:
            t = t.strip().upper().replace("/", "-")
            if not TICKER_RE.match(t):
                raise ValueError(f"Invalid ticker: {t!r}")
            if t not in out:
                out.append(t)
        return out

    @model_validator(mode="after")
    def _non_empty(self) -> "Universe":
        if not self.tickers and not self.preset:
            raise ValueError("Provide at least one ticker (tickers) or a preset group (preset)")
        if len(self.resolve()) > MAX_TICKERS:
            raise ValueError(f"At most {MAX_TICKERS} tickers per strategy")
        return self

    def resolve(self) -> list[str]:
        out = list(self.tickers)
        for t in PRESETS.get(self.preset or "", []):
            if t not in out:
                out.append(t)
        return out


class Risk(_Strict):
    stop_loss_pct: Optional[float] = Field(None, gt=0, le=50)
    take_profit_pct: Optional[float] = Field(None, gt=0, le=500)
    trailing_stop_pct: Optional[float] = Field(None, gt=0, le=50)
    atr_stop_mult: Optional[float] = Field(None, gt=0, le=10, description="Stop = entry price - k × ATR(14)")


class AlertPrefs(_Strict):
    on: list[Literal["entry", "exit"]] = Field(default_factory=lambda: ["entry", "exit"])
    cooldown_bars: int = Field(3, ge=0, le=60, description="Do not re-alert the same ticker for N sessions after an exit")


class Strategy(_Strict):
    name: str = Field(min_length=1, max_length=80)
    description: Optional[str] = Field(None, max_length=500)
    universe: Universe
    timeframe: Literal["1d"] = "1d"
    entry: Condition
    exit: Optional[Condition] = None
    risk: Risk = Field(default_factory=Risk)
    alert: AlertPrefs = Field(default_factory=AlertPrefs)

    @model_validator(mode="after")
    def _limits(self) -> "Strategy":
        for label, cond in (("entry", self.entry), ("exit", self.exit)):
            if cond is None:
                continue
            depth, count = _measure(cond)
            if depth > MAX_DEPTH:
                raise ValueError(f"{label}: groups nested too deeply (max {MAX_DEPTH} levels)")
            if count > MAX_CONDITIONS:
                raise ValueError(f"{label}: too many conditions (max {MAX_CONDITIONS})")
        return self

    def has_exit_rule(self) -> bool:
        r = self.risk
        return self.exit is not None or any(
            v is not None for v in (r.stop_loss_pct, r.take_profit_pct, r.trailing_stop_pct, r.atr_stop_mult)
        )


def _measure(cond: Any, depth: int = 1) -> tuple[int, int]:
    if isinstance(cond, Comparison):
        return depth, 1
    children = cond.all if isinstance(cond, AllOf) else cond.any if isinstance(cond, AnyOf) else [cond.not_]
    max_depth, total = depth, 0
    for child in children:
        d, c = _measure(child, depth + 1)
        max_depth, total = max(max_depth, d), total + c
    return max_depth, total


def iter_operands(cond: Any):
    """Yield every operand referenced in a condition tree."""
    if isinstance(cond, Comparison):
        yield cond.left
        yield cond.right
        return
    children = cond.all if isinstance(cond, AllOf) else cond.any if isinstance(cond, AnyOf) else [cond.not_]
    for child in children:
        yield from iter_operands(child)


def warmup_bars(strategy: Strategy) -> int:
    """How many bars of history are needed before signals are reliable."""
    longest = 1
    for cond in (strategy.entry, strategy.exit):
        if cond is None:
            continue
        for op in iter_operands(cond):
            if isinstance(op, IndicatorRef):
                if op.ind.startswith("macd"):
                    need = (op.slow or 26) + (op.signal or 9)
                else:
                    need = op.resolved_period() + ((op.smooth or 3) if op.ind == "stoch_d" else 0)
                # Exponential indicators (EMA, RSI, ATR, ADX) need extra bars to converge.
                if op.ind in ("ema", "rsi", "atr", "adx") or op.ind.startswith("macd"):
                    need *= 3
                longest = max(longest, need + op.shift)
            elif isinstance(op, PriceRef):
                longest = max(longest, op.shift + 1)
    if strategy.risk.atr_stop_mult:
        longest = max(longest, 14 * 3)
    return longest + 2


_TAGS = {"number", "price", "indicator", "compare", "all", "any", "not"}


def _format_errors(err: ValidationError) -> list[str]:
    out = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"] if str(p) not in _TAGS)
        msg = e["msg"].removeprefix("Value error, ")
        out.append(f"{loc}: {msg}" if loc else msg)
    # Union errors repeat per branch; keep them short and unique.
    seen, uniq = set(), []
    for m in out:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq[:10]


def parse_strategy(data: dict | str) -> tuple[Optional[Strategy], list[str]]:
    """Validate raw JSON/dict into a Strategy. Returns (strategy, errors)."""
    try:
        if isinstance(data, str):
            return Strategy.model_validate_json(data), []
        return Strategy.model_validate(data), []
    except ValidationError as e:
        return None, _format_errors(e)


def strategy_json_schema() -> dict:
    return Strategy.model_json_schema(by_alias=True)
