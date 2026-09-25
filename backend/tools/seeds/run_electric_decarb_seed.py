"""
Bulk-seed electric_decarb_factors by reading CSVs directly.

Looks up all necessary IDs once, then inserts all rows in a single
execute_values() call — no per-row subqueries, no SQL-file encoding issues.

Run from the backend/ directory:
    python tools/seeds/run_electric_decarb_seed.py
"""
import csv
import os
from pathlib import Path

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:cmrt_2026@cmrt-psql-server-dev.postgres.database.azure.com:5432/cmrt_dev",
)
DATA_DIR = Path(__file__).parent / "data"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"

# (csv_filename, factor_type_code, has_region, is_percentage)
CSV_SPECS = [
    ("Final Data/Scope 2 emissions factors (location-based approach) (tCO2e_MWh).csv",  "scope2_location", True,  False),
    ("Final Data/Scope 2 emissions factors (market-based approach) (tCO2e_MWh).csv",    "scope2_market",   False, False),
    ("Final Data/Scope 3 emissions factors (location-based approach) (tCO2e_MWh).csv",  "scope3_location", True,  False),
    ("Final Data/Scope 3 emissions factors (market-based approach) (tCO2e_MWh).csv",    "scope3_market",   False, False),
    ("Final Data/Renewable Power Percentage (market-based approach).csv",               "renewable_pct",   False, False),
]

JUR_MAP = {"Australia": "Australia", "New Zealand": "New Zealand"}


def _parse_value(raw: str, is_pct: bool):
    """Return (value, qualifier) — both Python-native, ready for %s binding."""
    s = raw.strip()
    if not s or s.upper() == "N/A":
        return None, None
    if s.upper() == "D":
        return None, "D"
    try:
        num = float(s.rstrip("%")) / 100.0 if is_pct else float(s)
        return num, None
    except ValueError:
        return None, None


def main() -> None:
    print(f"Connecting to {DB_URL[:40]}...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # ── look up revision id ──────────────────────────────────────────────────
    cur.execute("SELECT id FROM dataset_revisions WHERE name = %s", (REVISION_NAME,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Dataset revision '{REVISION_NAME}' not found in DB")
    revision_id = row[0]
    print(f"  revision_id = {revision_id}")

    # ── look up jurisdiction ids ─────────────────────────────────────────────
    cur.execute("SELECT id, name FROM jurisdictions")
    jur_id = {name: _id for _id, name in cur.fetchall()}
    print(f"  jurisdictions loaded: {list(jur_id.keys())}")

    # ── look up grid_region ids ──────────────────────────────────────────────
    cur.execute(
        "SELECT gr.id, j.name, gr.name FROM grid_regions gr JOIN jurisdictions j ON j.id = gr.jurisdiction_id"
    )
    region_id = {(j_name, r_name): r_id for r_id, j_name, r_name in cur.fetchall()}
    print(f"  grid_regions loaded: {len(region_id)} rows")

    # ── build rows ───────────────────────────────────────────────────────────
    rows: list[tuple] = []
    for csv_file, ft_code, has_region, is_pct in CSV_SPECS:
        path = DATA_DIR / csv_file
        if not path.exists():
            print(f"  WARNING: {csv_file} not found — skipping")
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)

        start_col = 2 if has_region else 1
        year_cols = [int(h.strip()) for h in header[start_col:]]

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader)
            for data_row in reader:
                if not data_row or not data_row[0].strip():
                    continue

                jur_csv = data_row[0].strip()
                jur_db = JUR_MAP.get(jur_csv, jur_csv)
                j_id = jur_id.get(jur_db)
                if j_id is None:
                    print(f"  WARNING: jurisdiction '{jur_db}' not found — skipping row")
                    continue

                if has_region:
                    r_name = data_row[1].strip() if len(data_row) > 1 else ""
                    r_id = region_id.get((jur_db, r_name))
                    if r_id is None:
                        print(f"  WARNING: region '{r_name}' for '{jur_db}' not found — skipping row")
                        continue
                else:
                    r_id = None

                for i, year in enumerate(year_cols):
                    raw_val = data_row[start_col + i] if start_col + i < len(data_row) else ""
                    val, qual = _parse_value(raw_val, is_pct)
                    rows.append((revision_id, ft_code, j_id, r_id, year, val, qual))

        print(f"  {ft_code}: built rows from {csv_file}")

    print(f"\nInserting {len(rows)} rows into electric_decarb_factors ...")
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO electric_decarb_factors
            (dataset_revision_id, factor_type_code, jurisdiction_id, region_id, year, value, value_qualifier)
        VALUES %s
        ON CONFLICT DO NOTHING
        """,
        rows,
        page_size=500,
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM electric_decarb_factors")
    final_count = cur.fetchone()[0]
    print(f"Rows in electric_decarb_factors: {final_count}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
