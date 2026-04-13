from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings, validate_async_driver

logger = structlog.get_logger()

engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    validate_async_driver(settings.database_url)

    is_serverless = settings.environment in {"production", "vercel"}
    engine_kwargs: dict[str, object] = {"echo": False, "pool_pre_ping": True}
    if is_serverless:
        # Serverless Postgres providers typically require short-lived connections.
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    db_engine = create_async_engine(settings.database_url, **engine_kwargs)

    @event.listens_for(db_engine.sync_engine, "connect")
    def _on_connect(_dbapi_connection, _connection_record) -> None:
        logger.info("db_connection_established", driver=db_engine.url.drivername)

    return db_engine


def get_engine() -> AsyncEngine:
    global engine
    if engine is None:
        engine = _build_engine()
    return engine


def AsyncSessionLocal() -> AsyncSession:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
