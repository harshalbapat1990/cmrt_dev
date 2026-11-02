from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.base import Base

# Import models to populate Base.metadata for autogenerate.
# Keep this as an allowlist via models/__init__.py so WIP models with missing
# dependencies don't break Alembic.
import models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url from environment
# Convert async postgresql+asyncpg URL to sync postgresql URL for Alembic
db_url = settings.database_url
if not db_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set DATABASE_URL (or database_url) in the environment "
        "or backend/.env.local before running Alembic."
    )
if "postgresql+asyncpg://" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
# ConfigParser treats percent signs as interpolation markers. Database URLs
# commonly contain percent-encoded credentials (for example, %40 for @), so
# escape them while storing the option; ConfigParser restores the original URL
# when Alembic reads sqlalchemy.url.
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Serialize upgrades from the application startup check, container
        # entrypoint, and concurrent deployment replicas.
        connection.exec_driver_sql("SELECT pg_advisory_lock(827314991204)")
        # The session lock survives this commit, while clearing SQLAlchemy's
        # implicit transaction lets Alembic manage migration transactions.
        connection.commit()
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            if connection.in_transaction():
                connection.rollback()
            connection.exec_driver_sql("SELECT pg_advisory_unlock(827314991204)")
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
