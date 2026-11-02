"""Ensure the database schema is at the repository's current Alembic heads."""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from core.config import settings

logger = logging.getLogger(__name__)


def _sync_database_url() -> str:
    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to check or upgrade the database schema.")

    url = make_url(database_url)
    if url.drivername == "postgresql+asyncpg":
        url = url.set(drivername="postgresql+psycopg2")
    return url.render_as_string(hide_password=False)


def _alembic_config(backend_root: Path, database_url: str) -> Config:
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    # Alembic's config parser uses percent interpolation; escape encoded URL
    # credentials before storing the URL in Config.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _upgrade_if_behind() -> tuple[set[str], set[str]]:
    backend_root = Path(__file__).resolve().parents[1]
    database_url = _sync_database_url()
    config = _alembic_config(backend_root, database_url)
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    engine = create_engine(database_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            current_heads = set(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()

    if current_heads != expected_heads:
        logger.info(
            "Database Alembic revisions %s differ from repository heads %s; upgrading.",
            sorted(current_heads),
            sorted(expected_heads),
        )
        command.upgrade(config, "heads")

        engine = create_engine(database_url, poolclass=NullPool)
        try:
            with engine.connect() as connection:
                current_heads = set(MigrationContext.configure(connection).get_current_heads())
        finally:
            engine.dispose()

        if current_heads != expected_heads:
            raise RuntimeError(
                "Alembic upgrade finished without reaching all repository heads. "
                f"Database heads: {sorted(current_heads)}; repository heads: {sorted(expected_heads)}."
            )
    else:
        logger.info("Database schema is already at Alembic heads %s.", sorted(expected_heads))

    return current_heads, expected_heads


async def ensure_latest_alembic_heads() -> None:
    """Check schema heads and upgrade to every repository head if needed.

    Alembic uses the synchronous psycopg2 driver in ``alembic/env.py``. Run it
    on a worker thread so startup does not block the event loop.
    """
    await asyncio.to_thread(_upgrade_if_behind)
