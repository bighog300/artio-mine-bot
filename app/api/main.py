import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import sanitize_database_url, settings, validate_env
from app.db.log_writer import configure_structlog_for_service

api_log_processor = configure_structlog_for_service("api")

logger = structlog.get_logger()


async def _wait_for_database(max_attempts: int = 30, base_delay_seconds: float = 1.0) -> None:
    """Retry database initialization/check during startup."""
    from app.db.database import AsyncSessionLocal, init_db

    for attempt in range(1, max_attempts + 1):
        try:
            if settings.environment not in {"production", "vercel"}:
                await init_db()

            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))

            logger.info("startup_database_ready", attempt=attempt)
            return
        except Exception as exc:
            if attempt == max_attempts:
                logger.exception(
                    "startup_database_failed",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                raise

            delay_seconds = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "startup_database_retry",
                attempt=attempt,
                max_attempts=max_attempts,
                retry_in_seconds=delay_seconds,
                error=str(exc),
            )
            await asyncio.sleep(delay_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await api_log_processor.start()
        validate_env()

        logger.info(
            "startup_database_config",
            database_url=sanitize_database_url(settings.database_url),
            environment=settings.environment,
            driver=(settings.database_url.split("://", 1)[0] if "://" in settings.database_url else "unknown"),
        )

        await _wait_for_database()

        if not settings.openai_api_key:
            logger.warning(
                "openai_not_configured",
                message="OPENAI_API_KEY not set — AI extraction will fail",
            )

        yield
    except Exception as exc:
        logger.exception("startup_failed", error=str(exc))
        raise
    finally:
        await api_log_processor.stop()


app = FastAPI(title="Artio Miner API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if settings.environment != "production"
    else [o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    try:
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "openai": "configured" if settings.openai_api_key else "not configured",
    }


@app.get("/health/db")
async def health_db():
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "healthy"}


# Include routers
from app.api.routes import export, images, logs, mine, pages, records, sources, stats  # noqa: E402
from app.api.routes import settings as settings_routes  # noqa: E402

app.include_router(sources.router, prefix="/api")
app.include_router(mine.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
