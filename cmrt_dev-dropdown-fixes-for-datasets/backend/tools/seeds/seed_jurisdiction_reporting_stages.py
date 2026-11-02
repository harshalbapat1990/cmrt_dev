"""
Seed script: jurisdiction_reporting_stages
Maps each jurisdiction to the ANZ reporting stages it uses, with
jurisdiction-specific names and sequences.

Idempotent — uses INSERT ... ON CONFLICT (jurisdiction_id, name) DO NOTHING.

NOTE: This seed depends on jurisdictions and ANZ reporting stages being seeded first, as it requires their IDs for the foreign key relationships. After running the prerequisite seeds, query the database to get the IDs for the relevant jurisdictions and ANZ stages, then populate the STAGE_MAPPINGS list below with the appropriate values before running this script.
ADMIN SETUP REQUIRED
Run seed_jurisdictions and seed_anz_reporting_stages FIRST, then
query the DB for their IDs and fill in the STAGE_MAPPINGS list.

Each entry requires:
  - jurisdiction_id: UUID of an existing jurisdiction
  - anz_reporting_stage_id: UUID of an existing ANZ stage
  - name: jurisdiction-specific stage name (must be unique per jurisdiction)
  - sequence: display order within the jurisdiction

Run from the backend/ directory:
    python -m tools.seeds.seed_jurisdiction_reporting_stages
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

# NOTE: This is a placeholder seed for jurisdiction reporting stages. Populate the STAGE_MAPPINGS list with actual mappings between jurisdictions and ANZ reporting stages, including jurisdiction-specific names and sequences, when available. Then run this script to insert the mappings into the database. Each mapping should have a unique combination of jurisdiction_id and name to avoid conflicts.
# ADMIN: populate this list after seeding jurisdictions + ANZ stages

STAGE_MAPPINGS: list[dict] = [
    # Example entry — replace UUIDs with real values from the DB:
    # {
    #     "jurisdiction_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    #     "anz_reporting_stage_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    #     "name": "Business Case",
    #     "sequence": 1,
    # },
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    if not STAGE_MAPPINGS:
        print("[seed_jurisdiction_reporting_stages] STAGE_MAPPINGS list is empty — 0 rows inserted.")
        print("  Edit tools/seeds/seed_jurisdiction_reporting_stages.py and add mappings.")
        print("  Run seed_jurisdictions and seed_anz_reporting_stages first to get the IDs.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for row in STAGE_MAPPINGS:
            result = await conn.execute(
                text(
                    "INSERT INTO jurisdiction_reporting_stages "
                    "  (id, jurisdiction_id, anz_reporting_stage_id, name, sequence, created_at) "
                    "VALUES "
                    "  (gen_random_uuid(), :jurisdiction_id, :anz_reporting_stage_id, :name, :sequence, now()) "
                    "ON CONFLICT (jurisdiction_id, name) DO NOTHING"
                ),
                row,
            )
            inserted += result.rowcount
        print(f"[seed_jurisdiction_reporting_stages] {inserted}/{len(STAGE_MAPPINGS)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
