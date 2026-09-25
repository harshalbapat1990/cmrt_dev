"""
Seed: operational_equipment — CSV-driven.

Reads: backend/tools/seeds/data/Operational Equipment.csv

CSV columns used:
  Group, Item, Power (kW), Hours of operation per day,
  Days of electricity consumption per year, Source/Comments

NOTE: 'Annual Electricity Consumption (MWh/year)' in the CSV is informational only —
it is derived as power_kw * hours_per_day * days_per_year / 1000 at read time
and is NOT stored in the database.

Behaviour:
- Inserts global rows (dataset_revision_id = NULL).
- Idempotent via ON CONFLICT on the partial unique index (item)
  WHERE dataset_revision_id IS NULL AND is_active = TRUE.

Run from backend/:
    python -m tools.seeds.seed_operational_equipment
"""
import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATA_DIR = Path(__file__).parent / "data"
CSV_FILE = DATA_DIR / "Final Data" / "Operational Equipment.csv"


def _parse_decimal(raw: str) -> Decimal:
    cleaned = raw.strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse numeric value: {raw!r}") from exc


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = skipped = 0

    async with async_session() as session:
        # Delete all global rows (dataset_revision_id IS NULL) then re-insert
        await session.execute(
            text("DELETE FROM operational_equipment WHERE dataset_revision_id IS NULL")
        )

        with open(CSV_FILE, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                group_name = row["Group"].strip()
                item = row["Item"].strip()
                source = row.get("Source/Comments", "").strip() or None

                try:
                    power_kw = _parse_decimal(row["Power (kW)"])
                    hours_per_day = _parse_decimal(row["Hours of operation per day"])
                    days_per_year = _parse_decimal(row["Days of electricity consumption per year"])
                except ValueError as e:
                    print(f"  [operational_equipment] WARNING: skipping row '{item}' — {e}")
                    skipped += 1
                    continue

                await session.execute(
                    text("""
                        INSERT INTO operational_equipment
                            (group_name, item, power_kw, hours_per_day, days_per_year, source, is_active)
                        VALUES
                            (:group_name, :item, :power_kw, :hours_per_day, :days_per_year, :source, TRUE)
                    """),
                    {
                        "group_name": group_name,
                        "item": item,
                        "power_kw": power_kw,
                        "hours_per_day": hours_per_day,
                        "days_per_year": days_per_year,
                        "source": source,
                    },
                )
                inserted += 1

        await session.commit()

    await engine.dispose()
    print(f"  [operational_equipment] {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed())
