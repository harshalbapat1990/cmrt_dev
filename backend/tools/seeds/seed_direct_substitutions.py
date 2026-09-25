"""
Seed: direct_substitution_factors — CSV-driven.

Reads:
  - backend/tools/seeds/data/Final Data/Australian Direct Substitutions Database.csv  (jurisdiction=Australia)
  - backend/tools/seeds/data/Final Data/New Zealand Direct Substitutions Database.csv  (jurisdiction=New Zealand)

CSV columns:
  User entered emissions source, Unit, BAU equivalent emission source,
  BAU equivalent unit, BAU quantity (per unit of user identified source)

Behaviour:
- DELETEs all existing rows for each jurisdiction before re-inserting (no backward compat).
- Assigns display_order = row index (0-based) within each file.
- Rows with missing required fields are skipped.

Run from backend/:
    python -m tools.seeds.seed_direct_substitutions
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

DATA_DIR = Path(__file__).parent / "data" / "Final Data"

SOURCES = [
    ("Australian Direct Substitutions Database.csv", "Australia"),
    ("New Zealand Direct Substitutions Database.csv", "New Zealand"),
]


def _parse_qty(raw: str) -> Optional[Decimal]:
    cleaned = raw.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Build jurisdiction name → id map
        r = await session.execute(text("SELECT id, name FROM jurisdictions"))
        jur_map: dict[str, str] = {name: str(jid) for jid, name in r.fetchall()}

        total_inserted = 0
        total_deleted = 0

        for csv_file, jur_name in SOURCES:
            path = DATA_DIR / csv_file
            if not path.exists():
                print(f"  WARNING: {csv_file} not found — skipping")
                continue

            jur_id = jur_map.get(jur_name)
            if jur_id is None:
                print(f"  WARNING: jurisdiction '{jur_name}' not found in DB — skipping {csv_file}")
                continue

            # Delete all existing rows for this jurisdiction (no backward compat)
            result = await session.execute(
                text("DELETE FROM direct_substitution_factors WHERE jurisdiction_id = :jid"),
                {"jid": jur_id},
            )
            deleted = result.rowcount
            total_deleted += deleted
            print(f"  [{jur_name}] deleted {deleted} existing rows")

            rows = []
            with open(path, newline="", encoding="utf-8-sig") as f:
                for display_order, row in enumerate(csv.DictReader(f)):
                    user_src = (row.get("User entered emissions source") or "").strip()
                    user_unit = (row.get("Unit") or "").strip()
                    bau_src = (row.get("BAU equivalent emission source") or "").strip()
                    bau_unit = (row.get("BAU equivalent unit") or "").strip()
                    qty_raw = row.get("BAU quantity (per unit of user identified source)", "")
                    bau_qty = _parse_qty(qty_raw)

                    if not user_src or not user_unit or not bau_src or not bau_unit or bau_qty is None:
                        print(f"    SKIP row {display_order + 2}: missing required field(s)")
                        continue

                    rows.append({
                        "jur_id": jur_id,
                        "user_src": user_src,
                        "user_unit": user_unit,
                        "bau_src": bau_src,
                        "bau_unit": bau_unit,
                        "bau_qty": str(bau_qty),
                        "display_order": display_order,
                    })

            for row_data in rows:
                await session.execute(
                    text(
                        """
                        INSERT INTO direct_substitution_factors
                            (jurisdiction_id, user_emissions_source, user_unit,
                             bau_equivalent_emission_source, bau_equivalent_unit,
                             bau_quantity_per_user_unit, display_order)
                        VALUES
                            (:jur_id, :user_src, :user_unit,
                             :bau_src, :bau_unit,
                             :bau_qty, :display_order)
                        """
                    ),
                    row_data,
                )

            total_inserted += len(rows)
            print(f"  [{jur_name}] inserted {len(rows)} rows")

        await session.commit()

    await engine.dispose()
    print(
        f"  [direct_substitution_factors] done — "
        f"{total_deleted} deleted, {total_inserted} inserted"
    )


if __name__ == "__main__":
    asyncio.run(seed())
