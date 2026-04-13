import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = structlog.get_logger()


def validate_env() -> None:
    """Fail fast if required env vars are missing."""
    required = ["DATABASE_URL"]
    if settings.environment == "production":
        required.append("OPENAI_API_KEY")

    missing = []
    for key in required:
        val = getattr(settings, key.lower(), None)
        if not val or (key == "OPENAI_API_KEY" and val == "sk-placeholder"):
            missing.append(key)

    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_env()
    # Skip schema creation in production — use `alembic upgrade head` instead.
    if settings.environment != "production":
        from app.db.database import init_db
        await init_db()
    if settings.openai_api_key == "sk-placeholder":
        logger.warning(
            "openai_not_configured",
            message="OPENAI_API_KEY not set — AI extraction will fail",
        )
    yield


app = FastAPI(title="Artio Miner API", version="1.0.0", lifespan=lifespan)

# In development allow all origins (no credentials required).
# In production restrict to the configured CORS_ORIGINS list.
if settings.environment != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health():
    try:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "openai": "configured" if settings.openai_api_key != "sk-placeholder" else "not configured",
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
