"""
Seed script: anz_reporting_stages
Inserts ANZ-level reporting stage definitions (name + sequence).
Idempotent — uses INSERT ... ON CONFLICT (name) DO NOTHING.

------------------------------------------------------------------
ADMIN SETUP REQUIRED
Add stage definitions to the ANZ_STAGES list below before running.
Each entry is {"name": "<stage name>", "sequence": <int>}.
Stages are sourced from the CMRT Requirements PDF (see project docs).
------------------------------------------------------------------

Run from the backend/ directory:
    python -m tools.seeds.seed_anz_reporting_stages
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

# ------------------------------------------------------------------ #
# ADMIN: populate this list from the CMRT Requirements document
# ------------------------------------------------------------------ #
ANZ_STAGES: list[dict] = [
    # Example entries — uncomment and adjust as required:
    # {"name": "Business Case",     "sequence": 1},
    # {"name": "Concept Design",    "sequence": 2},
    # {"name": "Preliminary Design","sequence": 3},
    # {"name": "Detailed Design",   "sequence": 4},
    # {"name": "Construction",      "sequence": 5},
    # {"name": "Operation",         "sequence": 6},
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    if not ANZ_STAGES:
        print("[seed_anz_reporting_stages] ANZ_STAGES list is empty — 0 rows inserted.")
        print("  Edit tools/seeds/seed_anz_reporting_stages.py and add stage definitions.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for stage in ANZ_STAGES:
            result = await conn.execute(
                text(
                    "INSERT INTO anz_reporting_stages (id, name, sequence, created_at) "
                    "VALUES (gen_random_uuid(), :name, :sequence, now()) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                stage,
            )
            inserted += result.rowcount
        print(f"[seed_anz_reporting_stages] {inserted}/{len(ANZ_STAGES)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
