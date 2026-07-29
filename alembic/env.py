from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app import models  # noqa: F401
from app.core.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Return the configured database URL as a plain string.

    This remains compatible whether ``settings.database_url`` is stored as a
    string or as a Pydantic database URL object.
    """

    return str(settings.database_url)


def get_sync_database_url() -> str:
    """
    Return a synchronous database URL for Alembic offline mode.

    The application uses asyncpg at runtime, while offline SQL generation uses
    SQLAlchemy's synchronous PostgreSQL dialect.
    """

    return get_database_url().replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )


def configure_migration_context(**kwargs: Any) -> None:
    """
    Apply shared Alembic configuration.

    Type and server-default comparison are enabled so autogenerate detects
    meaningful model changes such as column type changes and database defaults.
    """

    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """
    Run migrations without establishing a database connection.
    """

    configure_migration_context(
        url=get_sync_database_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations through the synchronous connection exposed by SQLAlchemy's
    asynchronous connection bridge.
    """

    configure_migration_context(
        connection=connection,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations using the application's asynchronous database driver.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section) or {},
        url=get_database_url(),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
