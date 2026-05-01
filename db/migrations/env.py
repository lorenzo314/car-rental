"""Alembic migration environment.

Supports both offline (SQL script generation) and online (live DB)
migration modes.

Autogenerate
------------
Run ``alembic revision --autogenerate -m "description"`` to generate a
new migration based on the diff between the current schema and the ORM
models.  Alembic detects this by comparing ``target_metadata`` (derived
from all ORM models) against the live database.

Importing ``app.models`` is sufficient to register all tables on
``Base.metadata`` because the models package imports every model class
in its ``__init__.py``.
"""

import app.models  # noqa: F401 — registers all models on Base.metadata
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set the SQLAlchemy URL from our typed Settings (reads .env)
config.set_main_option("sqlalchemy.url", settings.db_url)

# Configure Python logging from alembic.ini if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object Alembic compares against for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without a live DB connection.

    Useful for generating SQL scripts to review or apply manually.
    Run with: ``alembic upgrade head --sql``
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
    """Apply migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
