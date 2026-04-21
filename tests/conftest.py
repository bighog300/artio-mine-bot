import os

# Force in-memory SQLite for all tests BEFORE any app module is imported.
# This ensures settings.database_url resolves to SQLite even when DATABASE_URL
# is set to a PostgreSQL URL in the developer's environment or .env file.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_API_TOKEN", "test-admin-token")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.database import Base  # noqa: E402

# In-memory SQLite: no disk writes, no directory pre-conditions, CI-safe.
# StaticPool ensures all operations share the single in-memory connection.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute(text("PRAGMA foreign_keys=OFF")))
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_client(db_session: AsyncSession):
    from app.api.main import app
    from app.api.deps import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Admin-Token": "test-admin-token"},
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_database_url():
    """Provide a clean test database URL for migration testing."""
    base_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/artio_test")
    sync_url = base_url.replace("+asyncpg", "")

    admin_url = sync_url.rsplit('/', 1)[0] + '/postgres'
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        admin_engine.dispose()
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available for migration tests: {exc}")

    yield base_url
