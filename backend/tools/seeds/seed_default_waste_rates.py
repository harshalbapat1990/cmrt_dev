"""
Seed: default_waste_rates

Placeholder — populate DEFAULT_WASTE_RATES below when authoritative data is available.
Requires jurisdictions, materials, waste_treatments, and (optionally) units to be seeded first.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.config import settings

# NOTE: This is a placeholder seed for default waste rates. Populate the DEFAULT_WASTE_RATES list with actual data when available, and then run this script to insert the rates into the database. Each rate should have a unique combination of jurisdiction, material, waste treatment, applicable lifecycle module code (if used), and basis to avoid conflicts.
# Add seed rows here.
# Format: (jurisdiction_name, material_name, waste_treatment_name, module_code, basis, rate, rate_unit_code, notes, eff_from, eff_to)
# Use None for optional fields.

DEFAULT_WASTE_RATES: list[tuple] = []


async def seed() -> None:
    if not DEFAULT_WASTE_RATES:
        print("  [default_waste_rates] No seed data defined — skipping.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for (jur_name, mat_name, wt_name, mod_code, basis, rate, rate_unit_code, notes, eff_from, eff_to) in DEFAULT_WASTE_RATES:
            jur_row = (await session.execute(text("SELECT id FROM jurisdictions WHERE name = :n"), {"n": jur_name})).fetchone()
            mat_row = (await session.execute(text("SELECT id FROM materials WHERE name = :n"), {"n": mat_name})).fetchone()
            wt_row = (await session.execute(text("SELECT id FROM waste_treatments WHERE name = :n"), {"n": wt_name})).fetchone()
            rate_unit_id = None
            if rate_unit_code:
                u_row = (await session.execute(text("SELECT id FROM units WHERE code = :c"), {"c": rate_unit_code})).fetchone()
                if u_row:
                    rate_unit_id = u_row[0]
            if not jur_row or not mat_row or not wt_row:
                print(f"  [default_waste_rates] WARNING: missing FK for row ({jur_name}, {mat_name}, {wt_name}) — skipping.")
                continue
            await session.execute(
                text("""
                    INSERT INTO default_waste_rates (jurisdiction_id, material_id, waste_treatment_id, applicable_lifecycle_module_code, basis, rate, rate_unit_id, notes, effective_from, effective_to)
                    VALUES (:jur_id, :mat_id, :wt_id, :mod_code, :basis, :rate, :rate_unit_id, :notes, :eff_from, :eff_to)
                    ON CONFLICT (jurisdiction_id, material_id, waste_treatment_id, applicable_lifecycle_module_code, basis) DO NOTHING
                """),
                {"jur_id": jur_row[0], "mat_id": mat_row[0], "wt_id": wt_row[0], "mod_code": mod_code, "basis": basis,
                 "rate": rate, "rate_unit_id": rate_unit_id, "notes": notes, "eff_from": eff_from, "eff_to": eff_to},
            )
        await session.commit()
    await engine.dispose()
    print(f"  [default_waste_rates] Seeded {len(DEFAULT_WASTE_RATES)} rows.")


if __name__ == "__main__":
    asyncio.run(seed())
