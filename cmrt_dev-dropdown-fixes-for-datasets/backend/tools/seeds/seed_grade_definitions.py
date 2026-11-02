"""
Seed script: grade_definitions
Inserts the 4 fixed grade rows (Grade 1–4) used to classify benchmark metrics.
Idempotent — uses INSERT ... ON CONFLICT DO NOTHING.

Run from the backend/ directory:
    python -m tools.seeds.seed_grade_definitions
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

GRADES = [
    {"id": 1, "name": "Grade 1 – Asset Level (Order-of-Magnitude)"},
    {"id": 2, "name": "Grade 2 – Component Level (Indicative)"},
    {"id": 3, "name": "Grade 3 – Detailed (Measured / Modelled)"},
    {"id": 4, "name": "Grade 4 – Detailed (Verified / Certified)"},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in GRADES:
            result = await conn.execute(
                text(
                    "INSERT INTO grade_definitions (id, name) "
                    "VALUES (:id, :name) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_grade_definitions] {inserted}/{len(GRADES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
