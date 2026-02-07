"""Async SQLAlchemy engine and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from canpoli.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create async engine with appropriate options for the database type
_engine_kwargs: dict = {"echo": settings.database_echo}

# PostgreSQL-specific pool configuration (not supported by SQLite)
if "postgresql" in settings.database_url:
    if settings.is_lambda:
        # Lambda: Use NullPool to avoid connection pooling issues
        # Each Lambda invocation creates/closes connections
        # RDS Proxy handles connection pooling at the infrastructure level
        logger.info("Lambda environment detected - using NullPool")
        _engine_kwargs["poolclass"] = NullPool
    else:
        # Standard deployment: Use connection pooling
        _engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
                "pool_recycle": settings.database_pool_recycle,
                "pool_pre_ping": True,  # Verify connections before use
            }
        )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def _session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Internal session scope with error handling.

    This is the shared implementation for both FastAPI dependency injection
    and standalone context manager usage.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error("Database session error: %s", e, exc_info=True)
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in FastAPI:
        @router.get("/")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with _session_scope() as session:
        yield session


# Alias for use as a context manager outside request handlers
get_session_context = _session_scope
