from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o"
    database_url: str = "sqlite+aiosqlite:///./data/miner.db"
    artio_api_url: str | None = None
    artio_api_key: str | None = None
    max_crawl_depth: int = 3
    max_pages_per_source: int = 500
    crawl_delay_ms: int = 1000
    playwright_enabled: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
