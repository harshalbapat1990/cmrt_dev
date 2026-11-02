from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _SessionLocal

    if _SessionLocal is not None:
        return _SessionLocal

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set DATABASE_URL (or database_url) in backend/.env.local before starting the API."
        )

    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )
    _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _SessionLocal


async def get_session() -> AsyncSession:
    SessionLocal = _get_sessionmaker()
    async with SessionLocal() as session:
        yield session


def get_engine() -> AsyncEngine:
    _get_sessionmaker()  # ensure engine is initialised
    return _engine