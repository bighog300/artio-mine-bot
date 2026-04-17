import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_db
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

# CORS configuration
configured_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if IS_SERVERLESS:
    cors_origins = configured_origins
else:
    cors_origins = configured_origins or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=bool(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_public_api_usage(request, call_next):
    if not request.url.path.startswith("/v1/"):
        return await call_next(request)

    started = time.perf_counter()
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(status_code=401, content={"detail": "Missing X-API-Key header"})

    response = await call_next(request)

    try:
        from app.api.auth import hash_api_key
        from app.db import crud

        db_provider = request.app.dependency_overrides.get(get_db, get_db)
        db_gen = db_provider()
        session = await anext(db_gen)
        try:
            key = await crud.get_api_key_by_hash(session, hash_api_key(api_key))
            if key:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                await crud.create_api_usage_event(
                    session,
                    tenant_id=key.tenant_id,
                    api_key_id=key.id,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=max(1, elapsed_ms),
                )
        finally:
            await db_gen.aclose()
    except Exception:
        logger.exception("usage_tracking_failed")
    return response


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

    try:
        from app.queue import check_queue_health

        queue_health = check_queue_health()
        redis_status = "ok" if queue_health.redis_ok else "unavailable"
        workers_status = "available" if queue_health.workers_available else "unavailable"
    except Exception:
        logger.exception("health_queue_check_failed")
        redis_status = "unavailable"
        workers_status = "unavailable"

    return {
        "status": "ok",
        "version": "1.0.0",
        "db": db_status,
        "redis": redis_status,
        "workers": workers_status,
        "openai": "configured" if settings.openai_api_key else "not configured",
        "environment": settings.environment,
    }


# Include routers
from app.api.routes import api_keys, audit, backfill, crawl_runs, export, graph, images, intelligence, logs, mapping_presets, mine, operations, pages, public_v1, records, review, search, source_mapper, sources, stats, usage  # noqa: E402
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
app.include_router(audit.router, prefix="/api")
app.include_router(metrics_routes.router, prefix="/api")
app.include_router(operations.router, prefix="/api")
app.include_router(api_keys.router, prefix="/api")
app.include_router(usage.router, prefix="/api")
app.include_router(source_mapper.router, prefix="/api")
app.include_router(mapping_presets.router, prefix="/api")
app.include_router(crawl_runs.router, prefix="/api")
app.include_router(public_v1.router)
app.include_router(backfill.router, prefix="/api")
