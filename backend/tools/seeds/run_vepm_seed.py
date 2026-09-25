"""
Bulk-seed vepm_factors from the VEPM table CSV.

Row 1 is the header, row 2 is the units row (skip), data starts at row 3.
Heavy vehicle and Bus columns use comma-separated thousands — strip commas.

Run from the backend/ directory:
    python tools/seeds/run_vepm_seed.py
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
CSV_FILE = "VEPM Table.csv"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"


def _parse_num(raw: str):
    """Strip commas, return float or None."""
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

    # ── look up revision id ──────────────────────────────────────────────────
    cur.execute("SELECT id FROM dataset_revisions WHERE name = %s", (REVISION_NAME,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Dataset revision '{REVISION_NAME}' not found in DB")
    revision_id = row[0]
    print(f"  revision_id = {revision_id}")

    # ── parse CSV ────────────────────────────────────────────────────────────
    # Header: Year, Speed Car, Speed LCV, Speed HCV, Speed Bus,
    #         Fleet average, Light vehicle, Heavy vehicle, Bus
    # Col indices: 0=Year, 1=SpeedCar(=SpeedLCV=SpeedHCV=SpeedBus), 5=Fleet avg,
    #              6=Light vehicle, 7=Heavy vehicle, 8=Bus
    rows: list[tuple] = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row 1
        next(reader)  # skip units row 2

        for data_row in reader:
            if not data_row or not data_row[0].strip():
                continue

            year  = int(data_row[0].strip())
            speed = int(float(data_row[1].strip()))  # all 4 speed cols are equal
            fleet = _parse_num(data_row[5]) if len(data_row) > 5 else None
            light = _parse_num(data_row[6]) if len(data_row) > 6 else None
            heavy = _parse_num(data_row[7]) if len(data_row) > 7 else None
            bus   = _parse_num(data_row[8]) if len(data_row) > 8 else None

            rows.append((revision_id, year, speed, fleet, light, heavy, bus))

    print(f"\nBuilt {len(rows)} rows.")
    print("Inserting into vepm_factors ...")

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO vepm_factors
            (dataset_revision_id, year, speed_kmh,
             fleet_average_co2e_g_km, light_vehicle_co2e_g_km,
             heavy_vehicle_co2e_g_km, bus_co2e_g_km)
        VALUES %s
        ON CONFLICT ON CONSTRAINT uq_vepm_factors DO NOTHING
        """,
        rows,
        page_size=500,
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM vepm_factors WHERE dataset_revision_id = %s", (revision_id,))
    final_count = cur.fetchone()[0]
    print(f"Rows in vepm_factors for this revision: {final_count}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
