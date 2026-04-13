import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = structlog.get_logger()

app = FastAPI(title="Artio Miner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from app.db.database import init_db
    await init_db()
    if settings.openai_api_key == "sk-placeholder":
        logger.warning(
            "openai_not_configured",
            message="OPENAI_API_KEY not set — AI extraction will fail",
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

app.include_router(sources.router, prefix="/api")
app.include_router(mine.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
