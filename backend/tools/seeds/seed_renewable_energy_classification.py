"""
Seed: renewable_energy_classifications — CSV-driven.

Reads:
  - Renewable Energy Classification.csv  (workspace root — the authoritative source)

CSV structure (4 header/notes rows, then the column header row):
  Row 1: "Renewable Energy Classification,"
  Row 2: "Notes,"
  Row 3: "Classifications are based on definitions ..."
  Row 4: (blank)
  Row 5: Emissions Source, Classification   ← actual column header
  Row 6+: data rows

Behaviour:
- emissions_source and classification are stored as-is (trimmed strings).
- Rows with no Emissions Source are skipped.
- dataset_revision_id is NULL for all global/default rows.
- Idempotent: skips rows where (emissions_source) already exists as an active
  global row; updates classification and notes if the row exists but differs.

Run from backend/:
    python -m tools.seeds.seed_renewable_energy_classification
"""
from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings


DATA_CSV = Path(__file__).parent / "data" / "Final Data" / "Renewables Classification.csv"

# Number of notes/header rows to skip before the real column-header row
_NOTES_ROWS_TO_SKIP = 0


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        inserted = updated = skipped = 0

        with open(DATA_CSV, newline="", encoding="utf-8-sig") as fh:
            for _ in range(_NOTES_ROWS_TO_SKIP):
                next(fh)

            for row in csv.DictReader(fh):
                source = (row.get("Emissions Source") or "").strip()
                classification = (row.get("Classification") or "").strip()

                if not source:
                    skipped += 1
                    continue

                # Check for existing active global row
                existing = await session.execute(
                    text(
                        """
                        SELECT id, classification
                        FROM renewable_energy_classifications
                        WHERE emissions_source = :src
                          AND dataset_revision_id IS NULL
                          AND is_active = TRUE
                        LIMIT 1
                        """
                    ),
                    {"src": source},
                )
                row_existing = existing.fetchone()

                if row_existing is None:
                    await session.execute(
                        text(
                            """
                            INSERT INTO renewable_energy_classifications
                                (id, emissions_source, classification, dataset_revision_id, is_active)
                            VALUES (gen_random_uuid(), :src, :cls, NULL, TRUE)
                            """
                        ),
                        {"src": source, "cls": classification},
                    )
                    inserted += 1
                elif row_existing.classification != classification:
                    await session.execute(
                        text(
                            """
                            UPDATE renewable_energy_classifications
                            SET classification = :cls
                            WHERE id = :rid
                            """
                        ),
                        {"cls": classification, "rid": row_existing.id},
                    )
                    updated += 1
                else:
                    skipped += 1

        await session.commit()

    await engine.dispose()
    print(
        f"  [renewable_energy_classifications] "
        f"inserted={inserted}  updated={updated}  skipped={skipped}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
