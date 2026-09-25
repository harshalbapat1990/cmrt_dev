"""
Seed: recycled_content_factors — CSV-driven.

Reads:
  - Recycled Content.csv  (workspace root — the authoritative source)

CSV structure (after 5 header/notes rows):
  Jurisdiction, Emissions Sub-Category, Emissions Source,
  Recycled Content (%), Reused Content %, Source/Comments

Behaviour:
- Stores percentages as 0–1 fractions (e.g. "60%" → 0.60).
- Looks up jurisdiction_id from the jurisdictions table by name.
  Rows with an unrecognised jurisdiction are inserted with NULL jurisdiction_id.
- Looks up emissions_sub_category_id from emissions_categories by name.
  Rows with an unrecognised sub-category are inserted with NULL emissions_sub_category_id.
- Rows with no Emissions Source are skipped.
- Idempotent via ON CONFLICT (jurisdiction_id, emissions_source) DO UPDATE.

Run from backend/:
    python -m tools.seeds.seed_recycled_content_factors
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

# New CSV in Final Data folder (clean header, no notes rows)
DATA_CSV = Path(__file__).parent / "data" / "Final Data" / "Recycled Content.csv"
# Number of header/notes rows to skip before the actual column header
_NOTES_ROWS_TO_SKIP = 0


def _parse_percent(raw: str) -> Optional[Decimal]:
    """Convert '60%' → Decimal('0.60'); blank or unparseable → None."""
    cleaned = raw.strip().rstrip("%")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned) / Decimal("100")
    except InvalidOperation:
        return None


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Build lookup: jurisdictions.name → id
        r = await session.execute(text("SELECT id, name FROM jurisdictions"))
        jurisdiction_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}

        # Build lookup: emissions_categories.name → id (last-wins for duplicates)
        r = await session.execute(text("SELECT id, name FROM emissions_categories"))
        category_map: dict[str, str] = {n: str(i) for i, n in r.fetchall()}

        inserted = updated = skipped = unknown_jur = unknown_cat = 0

        with open(DATA_CSV, newline="", encoding="utf-8-sig") as fh:
            # Skip the leading notes rows before the real header line
            for _ in range(_NOTES_ROWS_TO_SKIP):
                next(fh)

            for row in csv.DictReader(fh):
                jur_name = (row.get("Jurisdiction") or "").strip()
                sub_cat_name = (row.get("Emissions Sub-Category") or "").strip()
                source = (row.get("Emissions Source") or "").strip()
                if not source:
                    skipped += 1
                    continue

                jur_id = jurisdiction_map.get(jur_name) if jur_name else None
                if jur_name and jur_id is None:
                    unknown_jur += 1

                sub_cat_id = category_map.get(sub_cat_name) if sub_cat_name else None
                if sub_cat_name and sub_cat_id is None:
                    unknown_cat += 1

                recycled_pct = _parse_percent(row.get("Recycled Content (%)", ""))
                reused_pct = _parse_percent(row.get("Reused Content %", ""))
                notes = (row.get("Source/Comments") or "").strip() or None

                res = await session.execute(
                    text("""
                        INSERT INTO recycled_content_factors
                            (id, jurisdiction_id, emissions_sub_category_id, emissions_source,
                             recycled_content_pct, reused_content_pct, notes)
                        VALUES (
                            gen_random_uuid(), :jur_id, :sub_cat_id, :src,
                            :recycled_pct, :reused_pct, :notes
                        )
                        ON CONFLICT (jurisdiction_id, emissions_source)
                        DO UPDATE SET
                            emissions_sub_category_id = EXCLUDED.emissions_sub_category_id,
                            recycled_content_pct      = EXCLUDED.recycled_content_pct,
                            reused_content_pct        = EXCLUDED.reused_content_pct,
                            notes                     = EXCLUDED.notes
                    """),
                    {
                        "jur_id":       jur_id,
                        "sub_cat_id":   sub_cat_id,
                        "src":          source,
                        "recycled_pct": str(recycled_pct) if recycled_pct is not None else None,
                        "reused_pct":   str(reused_pct)   if reused_pct   is not None else None,
                        "notes":        notes,
                    },
                )
                if res.rowcount:
                    inserted += 1
                else:
                    updated += 1

        await session.commit()

    await engine.dispose()
    print(
        f"  [recycled_content_factors] "
        f"{inserted} inserted/updated, {skipped} skipped (no source name), "
        f"{unknown_jur} rows with unrecognised jurisdiction (NULL jurisdiction_id), "
        f"{unknown_cat} rows with unrecognised sub-category (NULL emissions_sub_category_id)"
    )


if __name__ == "__main__":
    asyncio.run(seed())
