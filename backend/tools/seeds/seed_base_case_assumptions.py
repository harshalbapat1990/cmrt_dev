"""
Seed: base_case_assumptions

Placeholder — populate BASE_CASE_ASSUMPTIONS below when authoritative data is available.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.config import settings

# NOTE: This is a placeholder seed for base case assumptions. Populate the BASE_CASE_ASSUMPTIONS list with actual data when available, and then run this script to insert the assumptions into the database. Each assumption should have a unique combination of category and name to avoid conflicts.
# Add seed rows here.
# Format: (name, category, default_value, unit_code, is_anz_default, notes)
# Use None for optional fields.
# NOTE: category should reference an existing emissions category code from the emissions_categories table.
BASE_CASE_ASSUMPTIONS: list[tuple] = []


async def seed() -> None:
    if not BASE_CASE_ASSUMPTIONS:
        print("  [base_case_assumptions] No seed data defined — skipping.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for (name, category, default_value, unit_code, is_anz_default, notes) in BASE_CASE_ASSUMPTIONS:
            unit_id = None
            if unit_code:
                u_row = (await session.execute(text("SELECT id FROM units WHERE code = :c"), {"c": unit_code})).fetchone()
                if u_row:
                    unit_id = u_row[0]
            await session.execute(
                text("""
                    INSERT INTO base_case_assumptions (name, category, default_value, unit_id, is_anz_default, notes)
                    VALUES (:name, :category, :default_value, :unit_id, :is_anz_default, :notes)
                    ON CONFLICT (category, name) DO NOTHING
                """),
                {"name": name, "category": category, "default_value": default_value,
                 "unit_id": unit_id, "is_anz_default": is_anz_default, "notes": notes},
            )
        await session.commit()
    await engine.dispose()
    print(f"  [base_case_assumptions] Seeded {len(BASE_CASE_ASSUMPTIONS)} rows.")


if __name__ == "__main__":
    asyncio.run(seed())
