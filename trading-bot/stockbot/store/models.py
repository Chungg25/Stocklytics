"""Database schema (SQLAlchemy 2.0). Works on Postgres/Supabase and SQLite."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class BotUser(Base):
    """One Telegram user who owns one personal (managed) bot."""
    __tablename__ = "sb_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128))
    # Personal bot created via Telegram Managed Bots.
    bot_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    bot_username: Mapped[str | None] = mapped_column(String(64))
    bot_token_enc: Mapped[str | None] = mapped_column(Text)
    # Hash of the API key the user's Hermes uses to call our MCP server.
    api_key_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    # new -> provisioning -> awaiting_login -> active ; stopped
    status: Mapped[str] = mapped_column(String(24), default="new")
    container_name: Mapped[str | None] = mapped_column(String(128))
    # Optional position-sizing preferences.
    capital: Mapped[float | None] = mapped_column(Float)
    risk_pct: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    strategies: Mapped[list["StrategyRow"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class StrategyRow(Base):
    __tablename__ = "sb_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sb_users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    dsl: Mapped[dict] = mapped_column(JSON)
    # draft | active | paused | archived
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Latest backtest summary {"period":..., "portfolio":..., "per_ticker":...}
    last_backtest: Mapped[dict | None] = mapped_column(JSON)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[BotUser] = relationship(back_populates="strategies")


class Position(Base):
    """Virtual (paper) position opened when an entry alert is sent, so we know when to alert an exit."""
    __tablename__ = "sb_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("sb_strategies.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | closed | void
    provisional: Mapped[bool] = mapped_column(Boolean, default=True)  # opened intraday, not yet confirmed at close
    entry_date: Mapped[date] = mapped_column(Date)
    entry_price: Mapped[float] = mapped_column(Float)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stop: Mapped[float | None] = mapped_column(Float)
    target: Mapped[float | None] = mapped_column(Float)
    peak: Mapped[float] = mapped_column(Float)
    exit_date: Mapped[date | None] = mapped_column(Date)
    exit_price: Mapped[float | None] = mapped_column(Float)
    exit_reason: Mapped[str | None] = mapped_column(String(24))


class SignalEvent(Base):
    """Every alert we sent (or tried to send). The unique key prevents duplicates."""
    __tablename__ = "sb_signal_events"
    __table_args__ = (UniqueConstraint("strategy_id", "ticker", "kind", "session", name="uq_signal_once_per_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("sb_strategies.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(16))
    # entry | exit | stop_loss | trailing_stop | take_profit | invalidated
    kind: Mapped[str] = mapped_column(String(16))
    session: Mapped[date] = mapped_column(Date)
    price: Mapped[float] = mapped_column(Float)
    price_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(24))
    details: Mapped[dict | None] = mapped_column(JSON)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MutedTicker(Base):
    __tablename__ = "sb_muted_tickers"
    __table_args__ = (UniqueConstraint("strategy_id", "ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("sb_strategies.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(16))


class CheckRun(Base):
    """Audit log of each scheduled check (helps prove prices/timing were correct)."""
    __tablename__ = "sb_check_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(12))  # intraday | close
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tickers: Mapped[int] = mapped_column(Integer, default=0)
    alerts: Mapped[int] = mapped_column(Integer, default=0)
    stale: Mapped[dict | None] = mapped_column(JSON)
    errors: Mapped[dict | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
