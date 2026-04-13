import os
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to project root (app/config.py → app/ → project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent


STRICT_ENVIRONMENTS = {"production", "vercel"}


def ensure_data_dir() -> None:
    """Create <BASE_DIR>/data if it doesn't exist (idempotent)."""
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def get_database_url() -> str:
    """Return the database URL to use.

    Priority:
    1. DATABASE_URL env var
    2. Falls back to a local SQLite file for zero-config local dev

    Production example:
      DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.neon.tech/artio?sslmode=require
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Local dev fallback: absolute SQLite path so the app works without any config
    return f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'miner.db'}"


def normalize_database_url(url: str) -> str:
    """Normalize sync-style database URLs into async-driver URLs."""
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def sanitize_database_url(database_url: str) -> str:
    """Mask secrets in DATABASE_URL before logging it."""
    split = urlsplit(database_url)

    netloc = split.netloc
    if "@" in netloc:
        userinfo, hostinfo = netloc.rsplit("@", 1)
        username = userinfo.split(":", 1)[0] if userinfo else ""
        masked_userinfo = username if username else "***"
        netloc = f"{masked_userinfo}:***@{hostinfo}"

    safe_query_items = [
        (k, v if k.lower() in {"sslmode"} else "***")
        for k, v in parse_qsl(split.query, keep_blank_values=True)
    ]
    safe_query = "&".join(f"{k}={v}" for k, v in safe_query_items)

    return urlunsplit((split.scheme, netloc, split.path, safe_query, split.fragment))


def validate_async_driver(database_url: str) -> None:
    """Ensure DATABASE_URL is compatible with SQLAlchemy async engine."""
    if database_url.startswith("postgresql+asyncpg://"):
        return
    if database_url.startswith("sqlite+aiosqlite://"):
        return
    if database_url.startswith("postgresql://") or database_url.startswith(
        "postgresql+psycopg2://"
    ):
        raise RuntimeError(
            "Invalid DATABASE_URL for async SQLAlchemy. Use "
            "'postgresql+asyncpg://...' (not postgresql:// or postgresql+psycopg2://)."
        )
    if database_url.startswith("sqlite://"):
        raise RuntimeError(
            "Invalid SQLite async URL. Use 'sqlite+aiosqlite://...'."
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    database_url: str = get_database_url()
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int = 3
    max_pages_per_source: int = 500
    crawl_delay_ms: int = 1000
    # None means "use environment-based default": True in dev, False in production.
    playwright_enabled: bool | None = None
    cors_origins: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _set_playwright_default(self) -> "Settings":
        if self.playwright_enabled is None:
            self.playwright_enabled = self.environment != "production"
        return self

    @model_validator(mode="after")
    def _normalize_db_url(self) -> "Settings":
        if self.environment not in STRICT_ENVIRONMENTS:
            self.database_url = normalize_database_url(self.database_url)
        return self


settings = Settings()


def validate_env() -> None:
    required = ["DATABASE_URL"]

    if settings.environment == "production":
        required.append("OPENAI_API_KEY")

    missing = [
        key
        for key in required
        if not getattr(settings, key.lower(), None)
    ]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    validate_async_driver(settings.database_url)

    if settings.environment == "production" and "sqlite" in settings.database_url.lower():
        raise RuntimeError("SQLite is not supported in production. Use Postgres.")


def require_worker_environment() -> None:
    if settings.environment == "production":
        raise RuntimeError("This task must run in a worker environment, not Vercel.")
