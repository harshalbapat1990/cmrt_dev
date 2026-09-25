"""
Seed: electricity_recycling_assumptions — CSV-driven.

Reads:
  - backend/tools/seeds/data/Final Data/Electricity and recycling assumptions - Aus.csv  (AU)
  - backend/tools/seeds/data/Final Data/Electricity and recycling assumptions - NZ.csv   (NZ)

CSV columns:
  Metric, BAU %

Behaviour:
- DELETEs all existing global rows (dataset_revision_id IS NULL) per jurisdiction before re-inserting.
- Skips is_calculated=True metrics (grid_electricity_construction, grid_electricity_operation).
- Blank BAU % values are treated as 0.
- Inserts with dataset_revision_id = NULL (global/default rows).

Run from backend/:
    python -m tools.seeds.seed_electricity_recycling_assumptions
"""
from __future__ import annotations

import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATA_DIR = Path(__file__).parent / "data" / "Final Data"

SOURCES = [
    ("Electricity and recycling assumptions - Aus.csv", "Australia"),
    ("Electricity and recycling assumptions - NZ.csv", "New Zealand"),
]

# CSV metric label → (metric_code, metric_label_in_db, display_order)
# Skips is_calculated metrics (grid_electricity_*) which are not in the CSV.
CSV_METRIC_MAP: dict[str, tuple[str, str, int]] = {
    "On-site renewable energy use (Construction)":              ("onsite_renewable_construction",  "On-site renewable energy use (Construction)",  10),
    "Off-site renewable energy use (Construction)":             ("offsite_renewable_construction", "Off-site renewable energy use (Construction)", 20),
    "On-site renewable energy use (Operation)":                 ("onsite_renewable_operation",     "On-site renewable energy use (Operation)",     40),
    "Off-site renewable energy use (Operation)":                ("offsite_renewable_operation",    "Off-site renewable energy use (Operation)",    50),
    "Inert waste recycling (Concrete/ plastics / glass / rubble)": (
        "inert_waste_concrete_plastics_glass_rubble_recycling",
        "Inert waste - Concrete/ plastics / glass / rubble (Recycling)",
        70,
    ),
    "Inert waste recycling (Metals)":                           ("inert_waste_metals_recycling",   "Inert waste - Metals (Recycling)",             80),
    "Paper and cardboard recycling":                            ("paper_cardboard_recycling",      "Paper and cardboard (Recycling)",              90),
    "Garden and green recycling":                               ("garden_green_recycling",         "Garden and green (Recycling)",                100),
    "Wood recycling":                                           ("wood_recycling",                 "Wood (Recycling)",                            110),
    "Mixed construction and demolition waste recycling":        (
        "mixed_construction_demolition_waste_recycling",
        "Mixed construction and demolition waste (Recycling)",
        120,
    ),
}


def _parse_pct(raw: str) -> Decimal:
    """Parse BAU % value; blank or unparseable returns Decimal('0')."""
    cleaned = raw.strip().rstrip("%")
    if not cleaned:
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


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

            # Delete existing global rows for this jurisdiction
            result = await session.execute(
                text(
                    "DELETE FROM electricity_recycling_assumptions "
                    "WHERE jurisdiction_id = :jid AND dataset_revision_id IS NULL"
                ),
                {"jid": jur_id},
            )
            deleted = result.rowcount
            total_deleted += deleted
            print(f"  [{jur_name}] deleted {deleted} existing global rows")

            inserted = 0
            skipped = 0
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    metric_label_csv = (row.get("Metric") or "").strip()
                    if not metric_label_csv:
                        continue

                    mapping = CSV_METRIC_MAP.get(metric_label_csv)
                    if mapping is None:
                        print(f"    SKIP unknown metric label: '{metric_label_csv}'")
                        skipped += 1
                        continue

                    metric_code, metric_label_db, display_order = mapping
                    bau_pct = _parse_pct(row.get("BAU %", ""))

                    await session.execute(
                        text(
                            """
                            INSERT INTO electricity_recycling_assumptions
                                (jurisdiction_id, dataset_revision_id, metric_code, metric_label,
                                 default_bau_pct, is_calculated, display_order)
                            VALUES
                                (:jur_id, NULL, :metric_code, :metric_label,
                                 :bau_pct, FALSE, :display_order)
                            """
                        ),
                        {
                            "jur_id": jur_id,
                            "metric_code": metric_code,
                            "metric_label": metric_label_db,
                            "bau_pct": str(bau_pct),
                            "display_order": display_order,
                        },
                    )
                    inserted += 1

            total_inserted += inserted
            print(f"  [{jur_name}] inserted {inserted} rows ({skipped} skipped)")

        await session.commit()

    await engine.dispose()
    print(
        f"  [electricity_recycling_assumptions] done — "
        f"{total_deleted} deleted, {total_inserted} inserted"
    )


if __name__ == "__main__":
    asyncio.run(seed())
