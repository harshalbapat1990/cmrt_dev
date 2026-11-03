"""Fixtures for opt-in tests against an isolated, migrated PostgreSQL database."""

import os
from urllib.parse import urlsplit

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


def _integration_database_url() -> str:
    url = os.environ.get("CMRT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set CMRT_TEST_DATABASE_URL to run PostgreSQL integration tests")
    parsed_url = urlsplit(url)
    database = parsed_url.path.removeprefix("/")
    if database != "cmrt_test":
        raise RuntimeError(
            "PostgreSQL integration tests only permit the dedicated cmrt_test database; "
            "set CMRT_TEST_DATABASE_URL explicitly."
        )
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(
            "PostgreSQL integration tests only permit a local isolated database; "
            "remote hosts are rejected to prevent access to developer or production data."
        )
    return url


@pytest.fixture(scope="session")
def postgres_url() -> str:
    return _integration_database_url()


@pytest_asyncio.fixture
async def postgres_session(postgres_url):
    engine = create_async_engine(postgres_url, pool_pre_ping=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()
