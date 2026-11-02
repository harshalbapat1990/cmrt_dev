"""
Seed: densities — CSV-driven for both dataset levels.

Reads:
 - backend/tools/seeds/data/Component-Level Densities.csv (dataset='component')
 - backend/tools/seeds/data/Detailed-Level Densities.csv  (dataset='detailed')

Behaviour:
- Normalises Unicode superscripts in unit codes (m³→m3, m²→m2).
- Auto-inserts any unit codes not yet in the `units` table.
- Ensures the jurisdiction exists (looks up by name; skips row if not found).
- Uses emissions taxonomy for BOTH component and detailed datasets.
- Computes a stable record_key from emissions-based business key.
- Includes dataset_revision_id when seeding (links to a named revision).
- Idempotent via ON CONFLICT DO NOTHING on (jurisdiction_id, dataset, record_key, unit_id).

Run from backend/:
 python -m tools.seeds.seed_densities
"""

from __future__ import annotations

import asyncio
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def safe_print(msg: str) -> None:
    """Print a message, safely handling encoding errors on Windows consoles."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Write directly to stdout buffer with UTF-8 encoding and error replacement
        sys.stdout.buffer.write((msg + '\n').encode('utf-8', errors='replace'))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings


DATA_DIR = Path(__file__).parent / "data"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"

_UNICODE_FIX = str.maketrans({
    "\u00b3": "3",
    "\u00b2": "2",
    "\u2070": "0",
    "\u00b9": "1",
})


def _norm_unit(code: str) -> str:
    return code.strip().translate(_UNICODE_FIX)


def _parse_density(raw: str) -> Optional[Decimal]:
    cleaned = raw.strip()
    if not cleaned or cleaned in {"-", "–"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _record_key(cat: str, sub: str, src: str) -> str:
    def clean(v: str) -> str:
        return " ".join(v.split()).strip()

    return "|".join(clean(p) for p in (cat, sub, src))


async def _ensure_unit(
    session: AsyncSession,
    code: str,
    unit_map: dict[str, str],
) -> str:
    if code in unit_map:
        return unit_map[code]

    await session.execute(
        text(
            """
            INSERT INTO units (id, code)
            VALUES (gen_random_uuid(), :code)
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": code},
    )

    r = await session.execute(
        text("SELECT id FROM units WHERE code = :code"),
        {"code": code},
    )
    uid = str(r.fetchone()[0])
    unit_map[code] = uid
    return uid


async def _seed_dataset(
    *,
    session: AsyncSession,
    dataset: str,  # "component" | "detailed"
    csv_name: str,
    unit_map: dict[str, str],
    jurisdiction_map: dict[str, str],
    category_map: dict[str, str],
    dataset_revision_id: str | None = None,
):
    inserted = skip_jur = skip_cat = skip_conflict = 0

    csv_path = DATA_DIR / csv_name
    
    # Try different encodings to find one that works with the expected column names
    encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252']
    required_columns = {'Jurisdiction', 'Emissions Category', 'Emissions Sub-Category', 
                       'Emissions Source', 'Density', 'Material Density Unit', 'Source'}
    
    fh = None
    for encoding in encodings_to_try:
        try:
            fh = open(csv_path, newline="", encoding=encoding)
            # Try to read header and validate columns exist
            reader = csv.DictReader(fh)
            if reader.fieldnames and required_columns.issubset(set(reader.fieldnames)):
                # Found working encoding, seek back to start
                fh.seek(0)
                break
            else:
                fh.close()
                fh = None
        except (UnicodeDecodeError, UnicodeError, AttributeError):
            if fh:
                fh.close()
            fh = None
            continue
    
    if fh is None:
        safe_print(f"ERROR: Could not read {csv_name} with any encoding")
        return inserted, skip_jur, skip_cat, skip_conflict
        
    with fh:
        batch = 0
        for row in csv.DictReader(fh):
            jur_name = row["Jurisdiction"].strip()
            jur_id = jurisdiction_map.get(jur_name)
            if jur_id is None:
                skip_jur += 1
                continue

            em_cat = row["Emissions Category"].strip()
            em_sub = row["Emissions Sub-Category"].strip()
            em_src = row["Emissions Source"].strip()

            em_cat_id = category_map.get(em_cat)
            em_sub_id = category_map.get(em_sub)

            if em_cat_id is None or em_sub_id is None:
                safe_print(
                    f"[densities/{dataset}] SKIP unknown category "
                    f"'{em_cat}' or sub '{em_sub}'"
                )
                skip_cat += 1
                continue

            density = _parse_density(row["Density"])
            unit_code = _norm_unit(row["Material Density Unit"])
            unit_id = await _ensure_unit(session, unit_code, unit_map)
            source = row["Source"].strip() or None

            rk = _record_key(em_cat, em_sub, em_src)

            res = await session.execute(
                text(
                    """
                    INSERT INTO densities
                    (
                        dataset_revision_id,
                        jurisdiction_id,
                        dataset,
                        record_key,
                        emissions_category_id,
                        emissions_sub_category_id,
                        emissions_source,
                        density,
                        unit_id,
                        source
                    )
                    VALUES
                    (
                        :rev, :j, :ds, :rk,
                        :ec, :esc, :esrc,
                        :d, :u, :s
                    )
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "rev": dataset_revision_id,
                    "j": jur_id,
                    "ds": dataset,
                    "rk": rk,
                    "ec": em_cat_id,
                    "esc": em_sub_id,
                    "esrc": em_src,
                    "d": str(density) if density is not None else None,
                    "u": unit_id,
                    "s": source,
                },
            )

            if res.rowcount:
                inserted += res.rowcount
            else:
                skip_conflict += 1

            batch += 1
            if batch % 100 == 0:
                await session.commit()

    return inserted, skip_jur, skip_cat, skip_conflict


async def seed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Look up dataset_revision_id
        r = await session.execute(
            text("SELECT id FROM dataset_revisions WHERE name = :name"),
            {"name": REVISION_NAME},
        )
        revision_row = r.fetchone()
        if not revision_row:
            raise RuntimeError(
                f"Dataset revision '{REVISION_NAME}' not found in database. "
                "Create it first or update REVISION_NAME in this script."
            )
        dataset_revision_id = str(revision_row[0])

        r = await session.execute(text("SELECT id, code FROM units"))
        unit_map = {c: str(i) for i, c in r.fetchall()}

        r = await session.execute(text("SELECT id, name FROM jurisdictions"))
        jurisdiction_map = {n: str(i) for i, n in r.fetchall()}

        r = await session.execute(text("SELECT id, name FROM emissions_categories"))
        category_map = {n: str(i) for i, n in r.fetchall()}

        c_ins, c_jur, c_cat, c_conf = await _seed_dataset(
            session=session,
            dataset="component",
            csv_name="Final Data/Component-Level Densities.csv",
            unit_map=unit_map,
            jurisdiction_map=jurisdiction_map,
            category_map=category_map,
            dataset_revision_id=dataset_revision_id,
        )

        d_ins, d_jur, d_cat, d_conf = await _seed_dataset(
            session=session,
            dataset="detailed",
            csv_name="Detailed-Level Densities.csv",
            unit_map=unit_map,
            jurisdiction_map=jurisdiction_map,
            category_map=category_map,
            dataset_revision_id=dataset_revision_id,
        )

        await session.commit()

    await engine.dispose()

    print(
        f"[densities] component: {c_ins} inserted, "
        f"{c_jur} unknown-jur, {c_cat} unknown-cat, {c_conf} already existed"
    )
    print(
        f"[densities] detailed : {d_ins} inserted, "
        f"{d_jur} unknown-jur, {d_cat} unknown-cat, {d_conf} already existed"
    )


if __name__ == "__main__":
    asyncio.run(seed())
