from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import ensure_data_dir, settings

_is_sqlite = settings.database_url.startswith("sqlite")
_is_serverless = settings.environment == "production" and not _is_sqlite

# SQLite:            needs check_same_thread=False; no pool_size support.
# Postgres (local):  real connection pool with pre-ping for resilience.
# Postgres (Neon/serverless): NullPool — no persistent connections allowed.
_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
elif _is_serverless:
    # Neon and other serverless Postgres providers require NullPool —
    # they close connections aggressively and pool_size causes exhaustion.
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.database_url, **_engine_kwargs)

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
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    # data/ directory only makes sense for SQLite; PostgreSQL manages its own storage
    if _is_sqlite:
        ensure_data_dir()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
