from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _create_application_engine() -> AsyncEngine:
    """
    Create the pooled async engine used by FastAPI requests.

    API requests normally run on the application's long-lived event loop, so
    standard connection pooling is appropriate and improves throughput.
    """

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


def _create_task_engine() -> AsyncEngine:
    """
    Create the non-pooled async engine used by synchronous Celery tasks.

    Celery tasks enter async code through asyncio.run(), which creates a new
    event loop for each invocation. NullPool prevents asyncpg connections from
    being reused across different event loops.
    """

    return create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )


engine = _create_application_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

task_engine = _create_task_engine()

TaskAsyncSessionLocal = async_sessionmaker(
    bind=task_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    """Provide one database session for a FastAPI request."""

    async with AsyncSessionLocal() as session:
        yield session
