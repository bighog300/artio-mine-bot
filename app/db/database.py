from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings, validate_async_driver

logger = structlog.get_logger()

validate_async_driver(settings.database_url)

_is_serverless = settings.environment in {"production", "vercel"}

_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if _is_serverless:
    # Serverless Postgres providers typically require short-lived connections.
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.database_url, **_engine_kwargs)


@event.listens_for(engine.sync_engine, "connect")
def _on_connect(_dbapi_connection, _connection_record) -> None:
    logger.info("db_connection_established", driver=engine.url.drivername)


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
