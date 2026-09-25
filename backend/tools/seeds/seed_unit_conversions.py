"""
Seed: unit_conversions — CSV-driven with SI-inversion validation.

Reads backend/tools/seeds/data/Unit Conversions.csv.
- Parses factors robustly (quoted thousands: "3,600"; scientific: 2.78E-04)
- For every pair (A→B, B→A): if factor_AB * factor_BA != 1 the row with the
  larger absolute exponent is treated as inverted and auto-corrected to
  1 / factor_other.  All corrections are logged.
- Inserts into unit_conversions, skipping unknown units.
- Idempotent via ON CONFLICT (from_unit_id, to_unit_id) WHERE dataset_revision_id IS NULL DO NOTHING.

Run from backend/:
    python -m tools.seeds.seed_unit_conversions
"""
from __future__ import annotations

import asyncio
import csv
import math
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings

DATA_DIR = Path(__file__).parent / "data"
CSV_PATH = DATA_DIR / "Final Data" / "Unit Conversions.csv"


def _parse_factor(raw: str) -> Decimal | None:
    """Parse a factor string that may have quoted thousands-separators or sci notation."""
    cleaned = raw.strip().strip('"').replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _validate_and_correct(
    rows: list[tuple[str, str, Decimal]]
) -> list[tuple[str, str, Decimal]]:
    """Check reciprocal consistency; auto-correct obvious SI-prefix inversions."""

    # Build a lookup: (from_code, to_code) → factor
    lookup: dict[tuple[str, str], Decimal] = {}
    for fr, to, f in rows:
        lookup[(fr, to)] = f

    corrected: list[tuple[str, str, Decimal]] = []
    seen: set[tuple[str, str]] = set()

    for (fr, to), factor in lookup.items():
        if (fr, to) in seen:
            continue
        seen.add((fr, to))

        reciprocal = lookup.get((to, fr))
        if reciprocal is None:
            corrected.append((fr, to, factor))
            continue

        seen.add((to, fr))
        product = float(factor) * float(reciprocal)

        if abs(product - 1.0) < 1e-6:
            # Consistent pair — keep both
            corrected.append((fr, to, factor))
            corrected.append((to, fr, reciprocal))
        else:
            # Inconsistent — choose the row whose factor has the smaller absolute
            # log10 value as the "anchor" and derive the other from 1/anchor.
            log_f = abs(math.log10(abs(float(factor)))) if float(factor) != 0 else 0
            log_r = abs(math.log10(abs(float(reciprocal)))) if float(reciprocal) != 0 else 0

            if log_r <= log_f:
                # reciprocal is the anchor; A→B = 1/reciprocal
                corrected_factor = Decimal(1) / reciprocal
                print(
                    f"  [unit_conversions] CORRECTED {fr}→{to}: "
                    f"{factor} → {corrected_factor:.6g} "
                    f"(anchored on {to}→{fr} = {reciprocal})"
                )
                corrected.append((fr, to, corrected_factor))
                corrected.append((to, fr, reciprocal))
            else:
                # factor is the anchor; B→A = 1/factor
                corrected_reciprocal = Decimal(1) / factor
                print(
                    f"  [unit_conversions] CORRECTED {to}→{fr}: "
                    f"{reciprocal} → {corrected_reciprocal:.6g} "
                    f"(anchored on {fr}→{to} = {factor})"
                )
                corrected.append((fr, to, factor))
                corrected.append((to, fr, corrected_reciprocal))

    return corrected


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    # 1. Parse CSV
    raw_rows: list[tuple[str, str, Decimal]] = []
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fr = row["Reference Unit"].strip()
            to = row["Converted Unit"].strip()
            factor = _parse_factor(row["Conversion factor"])
            if factor is None or factor == 0:
                print(f"  [unit_conversions] Skipping unparseable factor for {fr}→{to}")
                continue
            raw_rows.append((fr, to, factor))

    print(f"  [unit_conversions] Parsed {len(raw_rows)} rows from CSV.")

    # 2. Validate & auto-correct
    rows = _validate_and_correct(raw_rows)

    # 3. Seed
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = skipped_unknown = skipped_conflict = 0
    async with async_session() as session:
        # Build unit code → id lookup
        result = await session.execute(text("SELECT id, code FROM units"))
        unit_map: dict[str, str] = {code: str(uid) for uid, code in result.fetchall()}

        for (fr, to, factor) in rows:
            from_id = unit_map.get(fr)
            to_id = unit_map.get(to)
            if from_id is None or to_id is None:
                missing = [c for c, uid in [(fr, from_id), (to, to_id)] if uid is None]
                print(f"  [unit_conversions] SKIP unknown unit(s) {missing}: {fr}→{to}")
                skipped_unknown += 1
                continue

            res = await session.execute(
                text("""
                    INSERT INTO unit_conversions (from_unit_id, to_unit_id, dataset_revision_id, factor)
                    VALUES (:from_id, :to_id, :dataset_revision_id, :factor)
                    ON CONFLICT (from_unit_id, to_unit_id) WHERE dataset_revision_id IS NULL DO NOTHING
                """),
                {"from_id": from_id, "to_id": to_id, "dataset_revision_id": None, "factor": str(factor)},
            )
            if res.rowcount:
                inserted += 1
            else:
                skipped_conflict += 1

        await session.commit()
    await engine.dispose()

    print(
        f"  [unit_conversions] Done — "
        f"{inserted} inserted, {skipped_conflict} already existed, "
        f"{skipped_unknown} skipped (unknown unit)."
    )


if __name__ == "__main__":
    asyncio.run(seed())
