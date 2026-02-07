"""Pytest configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from canpoli.models.base import Base

# Set test database URL before importing app
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ["REDIS_URL"] = ""

from canpoli.database import get_session  # noqa: E402
from canpoli.main import app  # noqa: E402

from canpoli.config import get_settings  # noqa: E402
from canpoli import redis_client  # noqa: E402

# Test database URL (SQLite in-memory for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
POSTGIS_TEST_DATABASE_URL_ENV = os.environ.get("POSTGIS_TEST_DATABASE_URL")
POSTGIS_TEST_DATABASE_URL = POSTGIS_TEST_DATABASE_URL_ENV or (
    "postgresql+asyncpg://canpoli:canpoli_dev@localhost:5433/canpoli_test"
)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Ensure settings are reloaded when tests modify env vars."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_redis_client():
    """Avoid leaking Redis clients across tests."""
    redis_client._redis_client = None
    yield
    redis_client._redis_client = None


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def postgis_engine():
    """Create PostGIS test database engine."""
    engine = create_async_engine(
        POSTGIS_TEST_DATABASE_URL,
        echo=False,
    )
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        await engine.dispose()
        if POSTGIS_TEST_DATABASE_URL_ENV:
            raise
        pytest.skip(f"PostGIS unavailable: {exc}")
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def postgis_session(postgis_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create PostGIS test database session."""
    session_factory = async_sessionmaker(
        postgis_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database session."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
