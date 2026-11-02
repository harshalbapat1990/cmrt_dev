"""
Seed script: jurisdictions
Inserts jurisdictions (Australian states/territories, NZ, etc.).
Idempotent — uses INSERT ... ON CONFLICT (name) DO NOTHING.

NOTE: This is a foundational seed that should be run before others, as some seeds reference jurisdictions. However, it can be run independently and re-run as needed when jurisdiction names are updated or added.
ADMIN SETUP REQUIRED
Add jurisdiction names to the JURISDICTIONS list below before running.
Examples: "NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT", "NZ"

Run from the backend/ directory:
    python -m tools.seeds.seed_jurisdictions
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

# NOTE: jurisdiction names should match those used in the density and recycled-content CSVs, as well as the jurisdiction dropdown in the frontend staging model form, to ensure correct associations and user experience.
# ADMIN: populate this list before running the script

JURISDICTIONS: list[str] = [
    "Australia",   # National / default jurisdiction used in density & recycled-content CSVs
    "NSW",
    "VIC",
    "QLD",
    "SA",
    "WA",
    "TAS",
    "NT",
    "ACT",
    "NZ",
    "New Zealand",
    "National",
]


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    if not JURISDICTIONS:
        print("[seed_jurisdictions] JURISDICTIONS list is empty — 0 rows inserted.")
        print("  Edit tools/seeds/seed_jurisdictions.py and add jurisdiction names to the list.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        inserted = 0
        for name in JURISDICTIONS:
            result = await conn.execute(
                text(
                    "INSERT INTO jurisdictions (id, name, created_at) "
                    "VALUES (gen_random_uuid(), :name, now()) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"name": name},
            )
            inserted += result.rowcount
        print(f"[seed_jurisdictions] {inserted}/{len(JURISDICTIONS)} rows inserted.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
