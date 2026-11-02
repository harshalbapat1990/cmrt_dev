"""
Seed script: ghg_scopes
Inserts the 3 fixed GHG scope rows (Scope 1, 2, 3).
Idempotent — uses INSERT ... ON CONFLICT DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_ghg_scopes
"""
import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on sys.path when run as a module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

GHG_SCOPES = [
    {"id": 1, "name": "Scope 1 – Direct Emissions"},
    {"id": 2, "name": "Scope 2 – Indirect Energy Emissions"},
    {"id": 3, "name": "Scope 3 – Other Indirect Emissions"},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in GHG_SCOPES:
            result = await conn.execute(
                text(
                    "INSERT INTO ghg_scopes (id, name) VALUES (:id, :name) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_ghg_scopes] {inserted}/{len(GHG_SCOPES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
