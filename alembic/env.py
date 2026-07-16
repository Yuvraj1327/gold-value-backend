"""Alembic environment.

The database URL comes from `app.core.config.Settings` (i.e. from your
`.env`/real environment) rather than being hardcoded in `alembic.ini`, so
the same migrations run identically in dev, CI, and production.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import every model so Base.metadata is fully populated.
import app.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()


def _get_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Supabase Session / Transaction poolers don't always default
        # search_path to 'public'.  Set it explicitly so every DDL
        # statement resolves table names without a schema prefix.
        connect_args={"server_settings": {"search_path": "public"}},
    )

    async with connectable.connect() as connection:
        # Belt-and-suspenders: also SET search_path at the session level.
        await connection.execute(
            __import__("sqlalchemy").text("SET search_path TO public")
        )
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
