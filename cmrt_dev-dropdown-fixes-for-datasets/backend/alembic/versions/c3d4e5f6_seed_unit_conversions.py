"""Seed unit_conversions table with common bidirectional conversion factors

Revision ID: c3d4e5f6
Revises: b2c3d4e5
Create Date: 2025-07-24

Populates the unit_conversions table with bidirectional factors for the
common unit pairs used across the app's BGM, maintenance and activity data
tables.  Every pair is inserted with ON CONFLICT DO NOTHING so the migration
is safe to re-run and won't overwrite hand-edited data.

The unit IDs are resolved at run-time by querying the units table by code;
any code that doesn't exist in the database is silently skipped, which keeps
the migration forward-compatible with future unit additions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pairs: (from_code, to_code, factor)
# factor converts one unit of from_code into to_code units
_CONVERSION_PAIRS = [
    # ── Mass ────────────────────────────────────────────────────────────────
    ("t",   "kg",  "1000"),
    ("kg",  "t",   "0.001"),
    # ── Length ──────────────────────────────────────────────────────────────
    ("m",   "km",  "0.001"),
    ("km",  "m",   "1000"),
    # ── Area ────────────────────────────────────────────────────────────────
    ("m2",  "ha",  "0.0001"),
    ("ha",  "m2",  "10000"),
    # ── Volume ──────────────────────────────────────────────────────────────
    ("m3",  "L",   "1000"),
    ("L",   "m3",  "0.001"),
    ("m3",  "kL",  "1"),
    ("kL",  "m3",  "1"),
    ("L",   "kL",  "0.001"),
    ("kL",  "L",   "1000"),
    ("m3",  "ML",  "0.001"),
    ("ML",  "m3",  "1000"),
    ("L",   "ML",  "0.000001"),
    ("ML",  "L",   "1000000"),
    ("kL",  "ML",  "0.001"),
    ("ML",  "kL",  "1000"),
    # ── Thermal energy ──────────────────────────────────────────────────────
    ("kJ",  "MJ",  "0.001"),
    ("MJ",  "kJ",  "1000"),
    ("MJ",  "GJ",  "0.001"),
    ("GJ",  "MJ",  "1000"),
    ("kJ",  "GJ",  "0.000001"),
    ("GJ",  "kJ",  "1000000"),
    # ── Electrical energy ───────────────────────────────────────────────────
    ("kWh", "MWh", "0.001"),
    ("MWh", "kWh", "1000"),
    ("kWh", "GWh", "0.000001"),
    ("GWh", "kWh", "1000000"),
    ("MWh", "GWh", "0.001"),
    ("GWh", "MWh", "1000"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Build a code→id lookup once for all codes used in the pairs above.
    all_codes = set()
    for from_code, to_code, _ in _CONVERSION_PAIRS:
        all_codes.add(from_code)
        all_codes.add(to_code)

    rows = conn.execute(
        sa.text("SELECT id, code FROM units WHERE code = ANY(:codes)"),
        {"codes": list(all_codes)},
    ).fetchall()

    code_to_id = {row[1]: row[0] for row in rows}

    # Insert only pairs whose both units exist, skipping the rest.
    inserted = 0
    skipped = 0
    for from_code, to_code, factor in _CONVERSION_PAIRS:
        from_id = code_to_id.get(from_code)
        to_id = code_to_id.get(to_code)
        if from_id is None or to_id is None:
            skipped += 1
            continue

        conn.execute(
            sa.text(
                """
                INSERT INTO unit_conversions (id, from_unit_id, to_unit_id, factor)
                VALUES (gen_random_uuid(), :from_id, :to_id, :factor)
                ON CONFLICT (from_unit_id, to_unit_id) DO NOTHING
                """
            ),
            {"from_id": from_id, "to_id": to_id, "factor": factor},
        )
        inserted += 1

    print(f"unit_conversions seed: attempted {inserted} pairs, skipped {skipped} (unit not in DB).")


def downgrade() -> None:
    # Remove only the rows we know we inserted (matched by factor value, not
    # just by ID, so hand-edited rows with different factors are preserved).
    conn = op.get_bind()

    all_codes = set()
    for from_code, to_code, _ in _CONVERSION_PAIRS:
        all_codes.add(from_code)
        all_codes.add(to_code)

    rows = conn.execute(
        sa.text("SELECT id, code FROM units WHERE code = ANY(:codes)"),
        {"codes": list(all_codes)},
    ).fetchall()

    code_to_id = {row[1]: row[0] for row in rows}

    for from_code, to_code, factor in _CONVERSION_PAIRS:
        from_id = code_to_id.get(from_code)
        to_id = code_to_id.get(to_code)
        if from_id is None or to_id is None:
            continue
        conn.execute(
            sa.text(
                """
                DELETE FROM unit_conversions
                WHERE from_unit_id = :from_id
                  AND to_unit_id   = :to_id
                  AND factor       = :factor
                """
            ),
            {"from_id": from_id, "to_id": to_id, "factor": factor},
        )
