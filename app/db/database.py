from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import is_serverless_environment, settings, validate_async_driver
from app.db.base import Base

logger = structlog.get_logger()

engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    validate_async_driver(settings.database_url)

    is_serverless = is_serverless_environment()
    is_sqlite = settings.database_url.startswith("sqlite+aiosqlite:") or settings.database_url.startswith("sqlite:")

    engine_kwargs: dict[str, object] = {"echo": False}
    if is_sqlite:
        # Keep SQLite engine configuration minimal for test/dev compatibility.
        pass
    elif is_serverless:
        # Serverless Postgres providers typically require short-lived connections.
        engine_kwargs["poolclass"] = NullPool
        engine_kwargs["pool_pre_ping"] = True
    else:
        engine_kwargs["pool_pre_ping"] = True
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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        try:
            await conn.exec_driver_sql(
                "INSERT INTO tenants (id, name, is_active, created_at, updated_at) "
                "VALUES ('public', 'public', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT(id) DO NOTHING"
            )
        except Exception:
            logger.exception("default_tenant_seed_failed")
