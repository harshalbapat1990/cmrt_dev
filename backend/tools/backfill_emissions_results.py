"""Recalculate activity rows into the structured emissions_results ledger.

Run from backend after upgrading the er01_result_dimensions migration:
    python -m tools.backfill_emissions_results [--project-id UUID]
"""
from __future__ import annotations

import argparse
import asyncio
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text

from core.session import _get_sessionmaker
from models.activity_data import ActivityData
from services.emissions_calculator import calculate_and_store


async def backfill(project_id: Optional[UUID]) -> int:
    SessionLocal = _get_sessionmaker()
    processed = 0
    async with SessionLocal() as db:
        dimension_columns = set((await db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'emissions_results'
        """))).scalars().all())
        required_columns = {
            "source_category", "emissions_scope", "accounting_basis", "reporting_measure"
        }
        missing = sorted(required_columns - dimension_columns)
        if missing:
            raise RuntimeError(
                "The emissions_results schema is missing required columns: "
                + ", ".join(missing)
                + ". Apply database migrations first with `alembic upgrade heads`, "
                "then rerun this backfill."
            )
        batch_size = 100
        while True:
            query = select(ActivityData).order_by(ActivityData.created_at, ActivityData.id)
            if project_id:
                query = query.where(ActivityData.project_id == project_id)
            batch = (await db.execute(query.offset(processed).limit(batch_size))).scalars().all()
            if not batch:
                break
            for row in batch:
                activity_row_id = row.id
                await calculate_and_store(db, row)
                if not db.in_transaction():
                    raise RuntimeError(
                        f"Calculation failed for activity_data {activity_row_id}; see the preceding error log. "
                        "Backfill stopped so the failed row is not silently skipped."
                    )
                processed += 1
            # Each query is fully consumed before commit, so no server-side
            # cursor is left open across transaction boundaries.
            await db.commit()
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", type=UUID, help="Limit recalculation to one project")
    args = parser.parse_args()
    count = asyncio.run(backfill(args.project_id))
    print(f"Recalculated {count} activity rows")


if __name__ == "__main__":
    main()
