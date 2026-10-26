"""MCP server the user's Hermes agent connects to (Streamable HTTP, bearer API key per user).

Deliberately exposes NO order-placing or brokerage tools: the system only analyses and notifies.
"""
from __future__ import annotations

import functools
from typing import Any, Callable

import anyio
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from stockbot import service

INSTRUCTIONS = """Stocklytics trading assistant tools (US stocks, daily candles).
Flow: strategy_schema → build the JSON → validate_strategy → show the summary to the user and get a yes →
run_backtest → explain results plainly → ask to turn alerts on → save_strategy + set_alerts(on=true).
This system NEVER places trades; it only sends notifications."""

mcp = MCPServer(name="stocklytics", instructions=INSTRUCTIONS, version="1.0.0")

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)


def _user_id(ctx: Context) -> int:
    headers = ctx.headers or {}
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    key = auth.removeprefix("Bearer ").strip()
    if not key:
        raise ToolError("Missing API key")
    try:
        return service.authenticate(key)
    except PermissionError as e:
        raise ToolError("Invalid API key — reconnect the bot from the Stocklytics manager bot") from e


async def _run(fn: Callable[..., Any], *args, **kwargs) -> Any:
    try:
        return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
    except service.UserError as e:
        raise ToolError(str(e)) from e


# ------------------------------------------------------------------ authoring
@mcp.tool(annotations=READ)
async def strategy_schema() -> dict:
    """JSON schema, presets, notes and an example for building a strategy. Call this before writing a strategy."""
    return service.schema()


@mcp.tool(annotations=READ)
async def validate_strategy(strategy: dict) -> dict:
    """Validate a strategy JSON. Returns a plain-English summary to read back to the user, or the errors to fix."""
    return await _run(service.validate, strategy)


@mcp.tool(annotations=READ)
async def run_backtest(ctx: Context, strategy_id: int | None = None, strategy: dict | None = None,
                       period: str = "3y", start_date: str | None = None, end_date: str | None = None,
                       capital: float = 10000) -> dict:
    """Backtest a saved strategy (strategy_id) or an unsaved one (strategy JSON) on real daily data.

    period: '1y', '3y', '5y', '6m' (ignored when start_date is given, ISO YYYY-MM-DD).
    A chart is sent to the user's chat automatically; you only need to explain the numbers.
    """
    uid = _user_id(ctx)
    if strategy_id is None and strategy is None:
        raise ToolError("Give strategy_id or strategy")
    return await _run(service.backtest, uid, strategy_id, strategy, period, start_date, end_date, capital)


@mcp.tool(annotations=WRITE)
async def save_strategy(ctx: Context, strategy: dict) -> dict:
    """Save a validated strategy (alerts stay OFF until set_alerts is called)."""
    return await _run(service.save_strategy, _user_id(ctx), strategy)


@mcp.tool(annotations=WRITE)
async def update_strategy(ctx: Context, strategy_id: int, strategy: dict) -> dict:
    """Replace a saved strategy's rules (keeps its alert on/off state)."""
    return await _run(service.update_strategy, _user_id(ctx), strategy_id, strategy)


@mcp.tool(annotations=READ)
async def list_strategies(ctx: Context) -> dict:
    """The user's strategies with status and last backtest headline numbers."""
    return await _run(service.list_strategies, _user_id(ctx))


@mcp.tool(annotations=READ)
async def get_strategy(ctx: Context, strategy_id: int) -> dict:
    """Full details of one strategy (rules, summary, muted tickers, last backtest)."""
    return await _run(service.get_strategy, _user_id(ctx), strategy_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True))
async def delete_strategy(ctx: Context, strategy_id: int) -> dict:
    """Delete a strategy and stop its alerts. Confirm with the user first."""
    return await _run(service.delete_strategy, _user_id(ctx), strategy_id)


# ------------------------------------------------------------------ alerts
@mcp.tool(annotations=WRITE)
async def set_alerts(ctx: Context, strategy_id: int, on: bool) -> dict:
    """Turn notifications for a strategy on (every 30 min in market hours + at the close) or off."""
    return await _run(service.set_alerts, _user_id(ctx), strategy_id, on)


@mcp.tool(annotations=WRITE)
async def mute_ticker(ctx: Context, strategy_id: int, ticker: str, muted: bool = True) -> dict:
    """Stop (or resume) alerts for one ticker inside a strategy."""
    return await _run(service.mute_ticker, _user_id(ctx), strategy_id, ticker, muted)


@mcp.tool(annotations=READ)
async def list_signals(ctx: Context, strategy_id: int | None = None, days: int = 14) -> dict:
    """Alerts already sent (buy/sell/stop/target/cancelled) with exact price, time and source.
    Use this when the user refers to an alert they received."""
    return await _run(service.list_signals, _user_id(ctx), strategy_id, days)


@mcp.tool(annotations=READ)
async def strategy_tracking(ctx: Context, strategy_id: int) -> dict:
    """Live (forward) results since alerts were enabled: open signals and closed signal returns."""
    return await _run(service.tracking, _user_id(ctx), strategy_id)


@mcp.tool(annotations=READ)
async def scan_now(ctx: Context, strategy_id: int) -> dict:
    """Check right now which tickers meet the strategy's BUY/SELL rules on the live timestamped price."""
    return await _run(service.scan_now, _user_id(ctx), strategy_id)


# ------------------------------------------------------------------ market data & settings
@mcp.tool(annotations=READ)
async def get_quote(ticker: str) -> dict:
    """Live price with the exact last-trade time (US stocks, Finnhub)."""
    return await _run(service.quote, ticker)


@mcp.tool(annotations=WRITE)
async def set_preferences(ctx: Context, capital: float | None = None, risk_pct: float | None = None) -> dict:
    """Account size and % risk per trade, used only to suggest position sizes in alerts."""
    return await _run(service.set_preferences, _user_id(ctx), capital, risk_pct)
