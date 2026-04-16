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
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/artio"
    )


def normalize_database_url(url: str) -> str:
    """Auto-convert sync driver URLs to async equivalents."""
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
    if database_url.startswith("postgresql+asyncpg://"):
        return
    if database_url.startswith("sqlite+aiosqlite://"):
        return
    if database_url.startswith("postgresql://") or database_url.startswith(
        "postgresql+psycopg2://"
    ):
        raise RuntimeError(
            "Invalid DATABASE_URL. Use 'postgresql+asyncpg://...' not 'postgresql://'."
        )
    raise RuntimeError(
        "Unsupported DATABASE_URL scheme. Use postgresql+asyncpg:// or sqlite+aiosqlite://"
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
    openai_required: bool = False
    database_url: str = get_database_url()
    redis_url: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int = 3
    max_pages_per_source: int = 500
    crawl_delay_ms: int = 1000
    use_deterministic_extraction: bool = True
    deterministic_confidence_threshold: int = 80
    max_ai_fallback_per_source: int = 50
    crawler_batch_size: int = 10
    crawler_rate_limit_ms: int = 1000
    crawler_respect_robots_txt: bool = True
    crawler_use_ai_fallback: bool = True
    crawler_allow_ai: bool = True
    crawler_require_runtime_map: bool = False
    # None means "use environment-based default": True in dev, False in production.
    playwright_enabled: bool | None = None
    cors_origins: str = "http://localhost:5173"
    max_concurrent_jobs: int = 5

    @model_validator(mode="after")
    def _set_playwright_default(self) -> "Settings":
        if self.playwright_enabled is None:
            self.playwright_enabled = self.environment not in STRICT_ENVIRONMENTS
        return self

    @model_validator(mode="after")
    def _normalize_db_url(self) -> "Settings":
        self.database_url = normalize_database_url(self.database_url)
        return self


settings = Settings()


def validate_env() -> None:
    if not settings.database_url:
        raise RuntimeError("Missing env var: DATABASE_URL")

    validate_async_driver(settings.database_url)

    if settings.openai_required and not settings.openai_api_key:
        raise RuntimeError("Missing env var: OPENAI_API_KEY")


def require_worker_environment() -> None:
    if settings.environment in STRICT_ENVIRONMENTS:
        raise RuntimeError("This task must run in a worker environment, not Vercel.")
