"""
Seed: default_transport_distances — CSV-driven.

Reads:
  - backend/tools/seeds/data/Transport distances v2.csv

Columns:
  Jurisdiction, Emissions Sub-Category,
  Truck Transport Mode, Rail Transport Mode, Sea Transport Mode,
  Truck (km), Rail (km), Sea (km), Source

Behaviour:
- Resolves Jurisdiction by name → jurisdictions.id (skips unknown).
- Resolves Emissions Sub-Category by name → emissions_categories.id (skips unknown).
- Stores all 3 per-mode distances + mode labels + source.
- Idempotent via ON CONFLICT (jurisdiction_id, emissions_category_id) DO NOTHING.

Run from backend/:
    python -m tools.seeds.seed_default_transport_distances
"""
from __future__ import annotations

import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATA_DIR = Path(__file__).parent / "data"
CSV_FILE = DATA_DIR / "Final Data" / "Transport Distance.csv"


def _parse_km(raw: str) -> Optional[Decimal]:
    cleaned = raw.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Check backend/.env.local")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        r = await session.execute(text("SELECT id, name FROM jurisdictions"))
        jur_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}

        r = await session.execute(text("SELECT id, name FROM emissions_categories"))
        cat_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}

        # All CSV distances are in km — resolve once
        r = await session.execute(text("SELECT id FROM units WHERE code = 'km'"))
        km_row = r.fetchone()
        km_unit_id = str(km_row[0]) if km_row else None
        if km_unit_id is None:
            print("  [default_transport_distances] WARNING: unit 'km' not found in units table — distance_unit_id will be NULL")

        inserted = skip_jur = skip_cat = 0
        rows_by_jur: dict[str, list[dict]] = {}

        with open(CSV_FILE, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                jur_name = row["Jurisdiction"].strip()
                sub_cat = row["Emissions Sub-Category"].strip()

                jur_id = jur_map.get(jur_name)
                if jur_id is None:
                    skip_jur += 1
                    continue

                cat_id = cat_map.get(sub_cat)
                if cat_id is None:
                    print(f"    [default_transport_distances] SKIP unknown sub-category '{sub_cat}'")
                    skip_cat += 1
                    continue

                rows_by_jur.setdefault(jur_id, []).append({
                    "jur": jur_id,
                    "cat": cat_id,
                    "truck_dist": str(v) if (v := _parse_km(row.get("Truck (km)", ""))) is not None else None,
                    "rail_dist": str(v) if (v := _parse_km(row.get("Rail (km)", ""))) is not None else None,
                    "sea_dist": str(v) if (v := _parse_km(row.get("Sea (km)", ""))) is not None else None,
                    "unit_id": km_unit_id,
                    "truck_mode": row.get("Truck Transport Mode", "").strip() or None,
                    "rail_mode": row.get("Rail Transport Mode", "").strip() or None,
                    "sea_mode": row.get("Sea Transport Mode", "").strip() or None,
                    "source": row.get("Source", "").strip() or None,
                })

        for jur_id, jur_rows in rows_by_jur.items():
            await session.execute(
                text("DELETE FROM default_transport_distances WHERE jurisdiction_id = :j"),
                {"j": jur_id},
            )
            # Deduplicate by (jur_id, cat_id) — keep last occurrence
            seen: dict[str, dict] = {}
            for r_data in jur_rows:
                seen[r_data["cat"]] = r_data
            for params in seen.values():
                await session.execute(text("""
                    INSERT INTO default_transport_distances
                        (jurisdiction_id, emissions_category_id,
                         truck_distance, rail_distance, sea_distance, distance_unit_id,
                         truck_transport_mode, rail_transport_mode, sea_transport_mode,
                         source)
                    VALUES
                        (:jur, :cat,
                         :truck_dist, :rail_dist, :sea_dist, :unit_id,
                         :truck_mode, :rail_mode, :sea_mode,
                         :source)
                """), params)
                inserted += 1

        await session.commit()

    await engine.dispose()
    print(
        f"  [default_transport_distances] {inserted} inserted, "
        f"{skip_jur} unknown-jur, {skip_cat} unknown-cat"
    )


if __name__ == "__main__":
    asyncio.run(seed())
