"""
Seed maintenance_replacement_factors from the Maintenance & Replacement CSV.

CSV columns: Jurisdiction, Activity Type, Item, Unit,
             Emissions intensity (tCO2e/UoM), Default frequency (years), Source/Comments

Run from the backend/ directory:
    python tools/seeds/seed_maintenance_replacement_factors.py
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
CSV_FILE = "Maintenance and Replacement.csv"
REVISION_NAME = "Austroads Benchmarks v1.0 (2026)"


def _parse_num(raw: str):
    s = raw.strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(raw: str):
    s = raw.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def main() -> None:
    path = DATA_DIR / "Final Data" / CSV_FILE
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    print(f"Connecting to {DB_URL[:40]}...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Resolve revision id
    cur.execute("SELECT id FROM dataset_revisions WHERE name = %s", (REVISION_NAME,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Dataset revision '{REVISION_NAME}' not found in DB")
    revision_id = row[0]
    print(f"  revision_id = {revision_id}")

    # Build jurisdiction id map
    cur.execute("SELECT id, name FROM jurisdictions")
    jur_map = {name: jur_id for jur_id, name in cur.fetchall()}
    print(f"  jurisdictions found: {list(jur_map.keys())}")

    cur.execute("SELECT id, code FROM units")
    unit_map = {code: unit_id for unit_id, code in cur.fetchall()}
    print(f"  units found: {list(unit_map.keys())}")

    insert_rows: list[tuple] = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for data_row in reader:
            jur_name = data_row.get("Jurisdiction", "").strip()
            activity_type = data_row.get("Activity Type", "").strip()
            item = data_row.get("Item", "").strip()
            unit_code = data_row.get("Unit", "m2").strip() or "m2"
            product_emissions = _parse_num(data_row.get("Product emissions (tCO2e)", ""))
            transport_emissions = _parse_num(data_row.get("Transport emissions (tCO2e)", ""))
            installation_emissions = _parse_num(data_row.get("Installation emissions (tCO2e)", ""))
            emissions_intensity = _parse_num(data_row.get("Emissions intensity (tCO2e/UoM)", ""))
            default_frequency = _parse_int(data_row.get("Default frequency (years)", ""))
            source_note = data_row.get("Source/Comments", "").strip() or None

            if not jur_name or not activity_type or not item:
                continue

            jur_id = jur_map.get(jur_name)
            if jur_id is None:
                print(f"  WARNING: jurisdiction '{jur_name}' not found — skipping: {item}")
                continue

            unit_id = unit_map.get(unit_code)
            if unit_id is None:
                print(f"  WARNING: unit '{unit_code}' not found in units table — skipping: {item}")
                continue

            insert_rows.append((
                revision_id,
                jur_id,
                activity_type,
                item,
                unit_id,
                product_emissions,
                transport_emissions,
                installation_emissions,
                emissions_intensity,
                default_frequency,
                source_note,
            ))

    print(f"\nBuilt {len(insert_rows)} rows.")
    print("Inserting into maintenance_replacement_factors ...")

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO maintenance_replacement_factors
            (dataset_revision_id, jurisdiction_id, activity_type, item,
             unit_id, product_emissions_tco2e, transport_emissions_tco2e,
             installation_emissions_tco2e, emissions_intensity_tco2e,
             default_frequency_years, source_note)
        VALUES %s
        ON CONFLICT ON CONSTRAINT uq_maintenance_replacement_factors DO NOTHING
        """,
        insert_rows,
        page_size=500,
    )
    conn.commit()

    cur.execute(
        "SELECT COUNT(*) FROM maintenance_replacement_factors WHERE dataset_revision_id = %s",
        (revision_id,),
    )
    final_count = cur.fetchone()[0]
    print(f"Rows in maintenance_replacement_factors for this revision: {final_count}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
