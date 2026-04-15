from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_env

logger = structlog.get_logger()

# Determine if running on serverless platform
# (where we need stricter CORS and different initialization)
IS_SERVERLESS = settings.environment in {"production", "vercel"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.database import init_db

    validate_env()

    if settings.environment not in {"production", "vercel", "docker"}:
        await init_db()

    if not settings.openai_api_key:
        logger.warning(
            "openai_not_configured",
            message="OPENAI_API_KEY not set — AI extraction will fail",
        )

    yield


app = FastAPI(title="Artio Miner API", version="1.0.0", lifespan=lifespan)

# CORS Configuration
# In development: allow all origins (localhost development)
# In production/serverless: restrict to configured origins only
cors_origins = (
    ["*"]
    if not IS_SERVERLESS
    else [o.strip() for o in settings.cors_origins.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint for monitoring and cold start detection.
    
    Returns:
        dict: Status of API, database, and OpenAI configuration
    """
    try:
        from app.db.database import AsyncSessionLocal
        import sqlalchemy
        async with AsyncSessionLocal() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "openai": "configured" if settings.openai_api_key else "not configured",
        "environment": settings.environment,
    }


# Include routers
from app.api.routes import export, graph, images, intelligence, logs, mine, pages, records, review, search, sources, stats  # noqa: E402
from app.api.routes import metrics as metrics_routes  # noqa: E402
from app.api.routes import settings as settings_routes  # noqa: E402

app.include_router(sources.router, prefix="/api")
app.include_router(mine.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(metrics_routes.router)
