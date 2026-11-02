"""
Bulk-seed freight_rail_factors from the Freight Rail CSV.

CSV columns: Train type, Terrain, Diesel fuel consumption (L per thousand GTK), Source/Comments

Run from the backend/ directory:
    python tools/seeds/run_freight_rail_seed.py
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
DATA_DIR = Path(__file__).parent / "data" / "Final Data"
CSV_FILE = "Freight Rail.csv"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"


def _parse_num(raw: str):
    s = raw.strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main() -> None:
    path = DATA_DIR / CSV_FILE
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    print(f"Connecting to {DB_URL[:40]}...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("SELECT id FROM dataset_revisions WHERE name = %s", (REVISION_NAME,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Dataset revision '{REVISION_NAME}' not found in DB")
    revision_id = row[0]
    print(f"  revision_id = {revision_id}")

    rows: list[tuple] = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row

        for data_row in reader:
            if not data_row or not data_row[0].strip():
                continue

            train_type  = data_row[0].strip()
            terrain     = data_row[1].strip()
            fuel_cons   = _parse_num(data_row[2]) if len(data_row) > 2 else None
            source_note = data_row[3].strip() if len(data_row) > 3 else None

            rows.append((revision_id, train_type, terrain, fuel_cons, source_note or None))

    print(f"\nBuilt {len(rows)} rows.")
    print("Inserting into freight_rail_factors ...")

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO freight_rail_factors
            (dataset_revision_id, train_type, terrain,
             fuel_consumption_l_per_000_gtk, source_note)
        VALUES %s
        ON CONFLICT ON CONSTRAINT uq_freight_rail_factors DO NOTHING
        """,
        rows,
        page_size=500,
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM freight_rail_factors WHERE dataset_revision_id = %s", (revision_id,))
    final_count = cur.fetchone()[0]
    print(f"Rows in freight_rail_factors for this revision: {final_count}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
