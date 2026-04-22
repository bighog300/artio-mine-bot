import asyncio
import time
from collections.abc import AsyncGenerator

import structlog
import sqlalchemy
from sqlalchemy import inspect
from sqlalchemy import event
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import is_serverless_environment, settings, validate_async_driver
from app.db.base import Base
from app.db.settings_store import load_user_settings

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
        engine_kwargs["connect_args"] = {
            "timeout": settings.db_connect_timeout_seconds,
            "command_timeout": settings.db_command_timeout_seconds,
        }
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout_seconds
        if settings.database_url.startswith("postgresql+asyncpg://"):
            engine_kwargs["connect_args"] = {
                "timeout": settings.db_connect_timeout_seconds,
                "command_timeout": settings.db_command_timeout_seconds,
            }

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


async def wait_for_database(
    *,
    max_wait_seconds: float | None = None,
    retry_interval_seconds: float | None = None,
) -> None:
    if settings.database_url.startswith("sqlite+aiosqlite://"):
        return

    effective_max_wait = (
        settings.db_startup_max_wait_seconds
        if max_wait_seconds is None
        else max_wait_seconds
    )
    effective_retry_interval = (
        settings.db_startup_retry_interval_seconds
        if retry_interval_seconds is None
        else retry_interval_seconds
    )
    deadline = time.monotonic() + effective_max_wait
    attempt = 0

    while True:
        attempt += 1
        try:
            async with get_engine().connect() as conn:
                await conn.execute(sqlalchemy.text("SELECT 1"))
            logger.info("db_wait_succeeded", attempt=attempt)
            return
        except (OperationalError, SQLAlchemyError, OSError, RuntimeError) as exc:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.error(
                    "db_wait_failed",
                    attempt=attempt,
                    timeout_seconds=effective_max_wait,
                    error=str(exc),
                )
                raise RuntimeError(
                    f"Database connection unavailable after {effective_max_wait:.1f}s"
                ) from exc

            logger.warning(
                "db_wait_retrying",
                attempt=attempt,
                retry_in_seconds=effective_retry_interval,
                remaining_seconds=max(0.0, remaining),
                error=str(exc),
            )
            await asyncio.sleep(min(effective_retry_interval, remaining))


async def init_db() -> None:
    async with get_engine().begin() as conn:
        tenants_table_exists = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table("tenants")
        )
        if tenants_table_exists:
            try:
                await conn.exec_driver_sql(
                    "INSERT INTO tenants (id, name, is_active, created_at, updated_at) "
                    "VALUES ('public', 'public', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(id) DO NOTHING"
                )
            except Exception:
                logger.exception("default_tenant_seed_failed")
        else:
            logger.info("default_tenant_seed_skipped", reason="tenants_table_missing")

        settings_table_exists = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table("settings")
        )

    user_settings: dict[str, str | None] = {
        "artio_api_url": None,
        "artio_api_key": None,
        "openai_api_key": None,
    }
    if settings_table_exists:
        async with AsyncSessionLocal() as session:
            user_settings = await load_user_settings(session)
    else:
        logger.info("user_settings_load_skipped", reason="settings_table_missing")

    if user_settings.get("artio_api_url") is not None:
        settings.artio_api_url = user_settings["artio_api_url"]
    if user_settings.get("artio_api_key") is not None:
        settings.artio_api_key = user_settings["artio_api_key"]
    if user_settings.get("openai_api_key") is not None:
        settings.openai_api_key = user_settings["openai_api_key"]
