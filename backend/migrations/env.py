"""Alembic migration environment."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    """Build the SQLAlchemy URL from ``MIGRATE_DATABASE_URL``.

    Returns:
        ``postgresql+psycopg://…`` URL for Alembic.

    Raises:
        RuntimeError: If ``MIGRATE_DATABASE_URL`` is unset.
    """
    url = os.environ.get("MIGRATE_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("MIGRATE_DATABASE_URL must be set for Alembic migrations")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live connection)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
