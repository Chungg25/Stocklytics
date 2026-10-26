"""Runtime configuration, read once from environment variables."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    # Public URL of this service (used for webhooks, MCP url given to Hermes, chart links).
    public_base_url: str = field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8100").rstrip("/"))
    # Postgres (Supabase) or SQLite connection string.
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./stockbot.db"))

    # Real-time quotes.
    finnhub_api_key: str = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))
    finnhub_calls_per_minute: int = field(default_factory=lambda: _int("FINNHUB_CALLS_PER_MINUTE", 55))
    # A live quote older than this (during regular hours) is treated as stale and never alerted on.
    max_quote_age_seconds: int = field(default_factory=lambda: _int("MAX_QUOTE_AGE_SECONDS", 300))

    # Telegram manager bot (the one users scan the QR for).
    manager_bot_token: str = field(default_factory=lambda: os.getenv("MANAGER_BOT_TOKEN", ""))
    manager_bot_username: str = field(default_factory=lambda: os.getenv("MANAGER_BOT_USERNAME", ""))
    telegram_webhook_secret: str = field(default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_SECRET", ""))

    # Fernet key used to encrypt bot tokens at rest.
    token_encryption_key: str = field(default_factory=lambda: os.getenv("TOKEN_ENCRYPTION_KEY", ""))

    # Hermes provisioning.
    hermes_image: str = field(default_factory=lambda: os.getenv("HERMES_IMAGE", "stocklytics/hermes-trader:latest"))
    hermes_data_root: str = field(default_factory=lambda: os.getenv("HERMES_DATA_ROOT", "/var/lib/stockbot/hermes"))
    hermes_network: str = field(default_factory=lambda: os.getenv("HERMES_DOCKER_NETWORK", ""))
    hermes_mem_limit: str = field(default_factory=lambda: os.getenv("HERMES_MEM_LIMIT", "768m"))
    # URL Hermes containers use to reach this service's MCP endpoint (may differ from the public URL).
    internal_mcp_url: str = field(default_factory=lambda: os.getenv("INTERNAL_MCP_URL", ""))

    # Scheduler.
    enable_scheduler: bool = field(default_factory=lambda: os.getenv("ENABLE_SCHEDULER", "true").lower() == "true")
    check_interval_minutes: int = field(default_factory=lambda: _int("CHECK_INTERVAL_MINUTES", 30))

    # Limits per user.
    max_strategies_per_user: int = field(default_factory=lambda: _int("MAX_STRATEGIES_PER_USER", 20))
    max_tickers_per_strategy: int = field(default_factory=lambda: _int("MAX_TICKERS_PER_STRATEGY", 30))

    @property
    def mcp_url_for_hermes(self) -> str:
        return (self.internal_mcp_url or f"{self.public_base_url}/mcp").rstrip("/")


settings = Settings()
