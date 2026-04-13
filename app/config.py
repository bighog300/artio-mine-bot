import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to project root (app/config.py → app/ → project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def ensure_data_dir() -> None:
    """Create <BASE_DIR>/data if it doesn't exist (idempotent)."""
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def get_database_url() -> str:
    """Return the database URL to use.

    Priority:
    1. DATABASE_URL env var (any value — postgres or sqlite both accepted)
    2. Falls back to a local SQLite file for zero-config local dev

    Production example:
      DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.neon.tech/artio?sslmode=require
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # Local dev fallback: absolute SQLite path so the app works without any config
    return f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'miner.db'}"


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

    if settings.environment == "production" and "sqlite" in settings.database_url.lower():
        raise RuntimeError("SQLite is not supported in production. Use Postgres.")


def require_worker_environment() -> None:
    if settings.environment == "production":
        raise RuntimeError("This task must run in a worker environment, not Vercel.")
