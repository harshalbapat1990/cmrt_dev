"""
Seed script: value_bands
Inserts the fixed Low / Mid / High band codes used in all grade benchmark CSV files.
Idempotent — uses INSERT ... ON CONFLICT DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_value_bands
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

VALUE_BANDS = [
    {"code": "Low",  "sort_order": 1},
    {"code": "Mid",  "sort_order": 2},
    {"code": "High", "sort_order": 3},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in VALUE_BANDS:
            result = await conn.execute(
                text(
                    "INSERT INTO value_bands (code, sort_order) "
                    "VALUES (:code, :sort_order) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_value_bands] {inserted}/{len(VALUE_BANDS)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
