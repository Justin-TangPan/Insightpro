"""Alembic env.py — configures migration runtime for InsightWeb.

Uses db._dsn() to resolve the Postgres URL and models.Base.metadata
for autogenerate support.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── InsightWeb: import DB DSN resolver and ORM metadata ──
from db import _dsn
from models import Base

config = context.config

# Override sqlalchemy.url from our DSN resolver (converts psycopg2 DSN to SQLAlchemy format)
_psycopg_dsn = _dsn()
# psycopg2 DSN uses postgres:// or postgresql:// — SQLAlchemy expects the same
config.set_main_option("sqlalchemy.url", _psycopg_dsn)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Make all ORM models visible to autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare types for accurate change detection
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
