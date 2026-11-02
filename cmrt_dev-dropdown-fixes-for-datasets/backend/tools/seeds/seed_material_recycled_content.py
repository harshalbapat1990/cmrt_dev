"""
Seed: material_recycled_content — CSV-driven.

Reads:
  - backend/tools/seeds/data/Final Data/Recycled Content.csv

Columns expected:
  Jurisdiction, Emissions Sub-Category, Emissions Source, Recycled Content (%),
  Reused Content %, Source/Comments

Behaviour:
- Ensures each unique "Emissions Source" name exists in materials table.
- Stores `percent` as a fraction 0–1 (e.g., "60%" → 0.60).
- Looks up jurisdiction by name; skips row if not found.
- Idempotent: deletes all global rows (dataset_revision_id IS NULL) per jurisdiction,
  then re-inserts. Uses DELETE+INSERT because the unique indexes are partial.

Run from backend/:
    python -m tools.seeds.seed_material_recycled_content
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
CSV_FILE = DATA_DIR / "Final Data" / "Recycled Content.csv"


def _parse_percent(raw: str) -> Optional[Decimal]:
    cleaned = raw.strip().rstrip("%")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned) / Decimal("100")
    except InvalidOperation:
        return None


async def _ensure_material(
    session: AsyncSession,
    name: str,
    emissions_category_id: Optional[str],
    mat_map: dict[str, str],
) -> str:
    if name in mat_map:
        return mat_map[name]
    await session.execute(
        text("""
            INSERT INTO materials (id, name, emissions_category_id)
            VALUES (gen_random_uuid(), :name, :cat_id)
            ON CONFLICT (name) DO NOTHING
        """),
        {"name": name, "cat_id": emissions_category_id},
    )
    r = await session.execute(text("SELECT id FROM materials WHERE name = :name"), {"name": name})
    mid = str(r.fetchone()[0])
    mat_map[name] = mid
    return mid


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        r = await session.execute(text("SELECT id, name FROM jurisdictions"))
        jur_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}
        r = await session.execute(text("SELECT id, name FROM materials"))
        mat_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}
        r = await session.execute(text("SELECT id, name FROM emissions_categories"))
        cat_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}

        # Read all rows first, grouped by jurisdiction
        rows_by_jur: dict[str, list[dict]] = {}
        skip_jur = 0
        with open(CSV_FILE, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                jurisdiction_name = row["Jurisdiction"].strip()
                jur_id = jur_map.get(jurisdiction_name)
                if jur_id is None:
                    skip_jur += 1
                    continue
                rows_by_jur.setdefault(jur_id, []).append(row)

        inserted = 0
        for jur_id, jur_rows in rows_by_jur.items():
            # Delete all global rows for this jurisdiction (partial index: dataset_revision_id IS NULL)
            await session.execute(
                text("DELETE FROM material_recycled_content WHERE jurisdiction_id = :j AND dataset_revision_id IS NULL"),
                {"j": jur_id},
            )
            # Deduplicate by (jur_id, mat_id) — keep last occurrence
            seen: dict[str, dict] = {}
            for row in jur_rows:
                material_name = row["Emissions Source"].strip()
                sub_cat = row["Emissions Sub-Category"].strip()
                emissions_category_id = cat_map.get(sub_cat)
                mat_id = await _ensure_material(session, material_name, emissions_category_id, mat_map)
                seen[mat_id] = {
                    "mat_id": mat_id,
                    "jur_id": jur_id,
                    "percent": _parse_percent(row["Recycled Content (%)"]),
                    "notes": row.get("Source/Comments", "").strip() or None,
                }
            for entry in seen.values():
                await session.execute(
                    text("""
                        INSERT INTO material_recycled_content
                            (id, material_id, jurisdiction_id, percent, notes)
                        VALUES (gen_random_uuid(), :m, :j, :p, :n)
                    """),
                    {"m": entry["mat_id"], "j": entry["jur_id"],
                     "p": str(entry["percent"]) if entry["percent"] is not None else None,
                     "n": entry["notes"]},
                )
                inserted += 1

        await session.commit()
    await engine.dispose()
    print(f"  [recycled_content] {inserted} inserted, {skip_jur} unknown-jur")


if __name__ == "__main__":
    asyncio.run(seed())
