import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to project root (app/config.py → app/ → project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def ensure_data_dir() -> None:
    """Create <BASE_DIR>/data if it doesn't exist (idempotent)."""
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


def get_database_url() -> str:
    """Return DB URL from DATABASE_URL env var, or an absolute SQLite path."""
    return os.environ.get("DATABASE_URL") or (
        f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'miner.db'}"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o"
    database_url: str = get_database_url()
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int = 3
    max_pages_per_source: int = 500
    crawl_delay_ms: int = 1000
    playwright_enabled: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
