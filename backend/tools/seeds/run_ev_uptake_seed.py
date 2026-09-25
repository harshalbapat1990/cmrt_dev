"""
Bulk-seed ev_uptake_factors from the Electric Vehicle Uptake CSV.

Run from the backend/ directory:
    python tools/seeds/run_ev_uptake_seed.py
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
CSV_FILE = "Electric Vehicle Uptake.csv"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"

# CSV region name → DB jurisdiction name (short form)
REGION_TO_JUR = {
    "New South Wales": "NSW",
    "QLD":             "QLD",
    "SA":              "SA",
    "TAS":             "TAS",
    "VIC":             "VIC",
    "WEM":             "WA",
}

# CSV scenario display name → DB code
SCENARIO_CODE = {
    "Slower Growth":          "slower_growth",
    "Step Change":            "step_change",
    "Accelerated Transition": "accelerated_transition",
}

# CSV vehicle category display name → DB code
VEHICLE_CATEGORY_CODE = {
    "Articulated Truck":       "articulated_truck",
    "Bus":                     "bus",
    "Large Light Commercial":  "large_light_commercial",
    "Large Residential":       "large_residential",
    "Medium Light Commercial": "medium_light_commercial",
    "Medium Residential":      "medium_residential",
    "Motorcycle":              "motorcycle",
    "Rigid Truck":             "rigid_truck",
    "Small Light Commercial":  "small_light_commercial",
    "Small Residential":       "small_residential",
}

# CSV energy type display name → DB code
ENERGY_TYPE_CODE = {
    "BEV":    "bev",
    "FCEV":   "fcev",
    "Hybrid": "hybrid",
    "ICE":    "ice",
    "PHEV":   "phev",
}


def _parse_pct(raw: str):
    """Return float or None. New CSV provides values as 0-1 fractions already."""
    s = raw.strip().rstrip("%")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_year_header(h: str) -> int:
    """Parse '2025-26' → 2025 (start year), or plain '2026' → 2026."""
    h = h.strip()
    if "-" in h:
        return int(h.split("-")[0])
    return int(h)


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

    # ── look up jurisdiction ids ─────────────────────────────────────────────
    cur.execute("SELECT id, name FROM jurisdictions")
    jur_id = {name: _id for _id, name in cur.fetchall()}
    print(f"  jurisdictions loaded: {sorted(jur_id.keys())}")

    # ── parse CSV and build rows ─────────────────────────────────────────────
    rows: list[tuple] = []
    skipped = 0

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Columns: Scenario, Region, Vehicle Category, Energy Type, 2025-26, 2026-27, ...
        year_cols = [_parse_year_header(h) for h in header[4:]]

        for data_row in reader:
            if not data_row or not data_row[0].strip():
                continue

            scenario_csv    = data_row[0].strip()
            region_csv      = data_row[1].strip()
            vehicle_csv     = data_row[2].strip()
            energy_type_csv = data_row[3].strip()

            jur_name = REGION_TO_JUR.get(region_csv)
            if jur_name is None:
                print(f"  WARNING: unknown region '{region_csv}' — skipping row")
                skipped += 1
                continue

            j_id = jur_id.get(jur_name)
            if j_id is None:
                print(f"  WARNING: jurisdiction '{jur_name}' not found in DB — skipping row")
                skipped += 1
                continue

            sc_code = SCENARIO_CODE.get(scenario_csv)
            if sc_code is None:
                print(f"  WARNING: unknown scenario '{scenario_csv}' — skipping row")
                skipped += 1
                continue

            vc_code = VEHICLE_CATEGORY_CODE.get(vehicle_csv)
            if vc_code is None:
                print(f"  WARNING: unknown vehicle category '{vehicle_csv}' — skipping row")
                skipped += 1
                continue

            et_code = ENERGY_TYPE_CODE.get(energy_type_csv)
            if et_code is None:
                print(f"  WARNING: unknown energy type '{energy_type_csv}' — skipping row")
                skipped += 1
                continue

            for i, year in enumerate(year_cols):
                raw_val = data_row[4 + i] if 4 + i < len(data_row) else ""
                val = _parse_pct(raw_val)
                rows.append((revision_id, j_id, sc_code, vc_code, et_code, year, val))

    print(f"\nBuilt {len(rows)} rows ({skipped} rows skipped).")
    print("Inserting into ev_uptake_factors ...")

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO ev_uptake_factors
            (dataset_revision_id, jurisdiction_id, scenario_code,
             vehicle_category_code, energy_type_code, year, uptake_pct)
        VALUES %s
        ON CONFLICT ON CONSTRAINT uq_ev_uptake_factors DO NOTHING
        """,
        rows,
        page_size=500,
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM ev_uptake_factors WHERE dataset_revision_id = %s", (revision_id,))
    final_count = cur.fetchone()[0]
    print(f"Rows in ev_uptake_factors for this revision: {final_count}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
