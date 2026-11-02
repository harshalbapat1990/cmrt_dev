"""
Seed script: dataset_revisions
Creates the initial "Austroads Benchmarks v1.0 (2026)" dataset revision that
the benchmark CSV import seeds will reference.
Idempotent — uses INSERT ... ON CONFLICT (name) DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_dataset_revisions
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

DATASET_REVISIONS = [
    {
        "name": "Austroads Benchmarks v1.0 (2026)",
        "applicable_from": date(2026, 1, 1),
        "applicable_to": None,
        "notes": (
            "Initial release of the Austroads CMRT grade benchmark dataset. "
            "Covers Grade 1 asset-level, Grade 2 component-level, and "
            "Grade 3 & 4 detailed (National Greenhouse Account) emission factors "
            "for Australia (AU) and New Zealand (NZ)."
        ),
    },
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in DATASET_REVISIONS:
            result = await conn.execute(
                text(
                    "INSERT INTO dataset_revisions "
                    "  (id, name, applicable_from, applicable_to, notes) "
                    "VALUES "
                    "  (gen_random_uuid(), :name, :applicable_from, :applicable_to, :notes) "
                    "ON CONFLICT (name, scope_type, scope_id) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_dataset_revisions] {inserted}/{len(DATASET_REVISIONS)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
