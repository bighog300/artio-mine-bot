from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import sanitize_database_url, settings, validate_env

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.db.database import init_db

        validate_env()

        logger.info(
            "startup_database_config",
            database_url=sanitize_database_url(settings.database_url),
            environment=settings.environment,
            driver=(settings.database_url.split("://", 1)[0] if "://" in settings.database_url else "unknown"),
        )

        if settings.environment not in {"production", "vercel"}:
            await init_db()

        if not settings.openai_api_key:
            logger.warning(
                "openai_not_configured",
                message="OPENAI_API_KEY not set — AI extraction will fail",
            )

        yield
    except Exception as exc:
        logger.exception("startup_failed", error=str(exc))
        raise


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
        import sqlalchemy
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.warning("health_db_check_failed", error=str(exc))
        db_status = "error"

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "openai": "configured" if settings.openai_api_key else "not configured",
    }


# Include routers
from app.api.routes import export, images, mine, pages, records, sources, stats  # noqa: E402
from app.api.routes import settings as settings_routes  # noqa: E402

app.include_router(sources.router, prefix="/api")
app.include_router(mine.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
