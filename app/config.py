import os
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

STRICT_ENVIRONMENTS = {"production", "vercel"}
BASE_DIR: Path = Path(__file__).resolve().parent.parent


def get_database_url() -> str:
    """Return DATABASE_URL from env or a Docker-friendly asyncpg default."""
    return os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://artio:artio@db:5432/artio_miner"
    )


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

    if database_url.startswith("postgresql://") or database_url.startswith(
        "postgresql+psycopg2://"
    ):
        raise RuntimeError(
            "Invalid DATABASE_URL for async SQLAlchemy. Use "
            "'postgresql+asyncpg://...' (sync PostgreSQL drivers are not supported)."
        )

    raise RuntimeError(
        "Invalid DATABASE_URL. This API only supports PostgreSQL with asyncpg "
        "('postgresql+asyncpg://...')."
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
            self.playwright_enabled = self.environment not in STRICT_ENVIRONMENTS
        return self


settings = Settings()


def validate_env() -> None:
    if not settings.database_url:
        raise RuntimeError("Missing env var: DATABASE_URL")

    validate_async_driver(settings.database_url)

    if settings.environment == "production" and not settings.openai_api_key:
        raise RuntimeError("Missing env var: OPENAI_API_KEY")


def require_worker_environment() -> None:
    if settings.environment in STRICT_ENVIRONMENTS:
        raise RuntimeError("This task must run in a worker environment, not Vercel.")
