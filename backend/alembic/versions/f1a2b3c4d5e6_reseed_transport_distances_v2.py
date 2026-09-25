"""Reseed default_transport_distances from Transport distances v2.

Revision ID: f1a2b3c4d5e6
Revises: ac2855f1ccb7
Create Date: 2026-04-01

Changes:
- DELETE all existing rows from default_transport_distances.
- INSERT new rows from Transport distances v2 data (National Embodied Carbon
  Databook v1.00 2026 + BRANZ NZ data).
- Resolves jurisdiction_id / emissions_category_id by name at migration time.
- Resolves distance_unit_id by unit code 'km'.
"""
from alembic import op
from sqlalchemy import text

revision = "f1a2b3c4d5e6"
down_revision = "ac2855f1ccb7"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# New dataset rows: (jurisdiction_name, emissions_sub_category, truck_mode,
#   rail_mode, sea_mode, truck_km, rail_km, sea_km, source)
# None means the original CSV had ' - ' (not applicable / zero).
# ---------------------------------------------------------------------------
_ROWS = [
    # Australia
    ("Australia", "Aggregate", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 40, None, None, "National Embodied Carbon Databook v1.00 2026 - Aggregates"),
    ("Australia", "Aluminium - extruded", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 720, None, 6800, "National Embodied Carbon Databook v1.00 2026 - Aluminium products"),
    ("Australia", "Cladding/roofing", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 370, None, 2600, "National Embodied Carbon Databook v1.00 2026 - Cladding and Roofing"),
    ("Australia", "Curtain wall", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "External shading system", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Glass", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Wall louvre system", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Windows & doors", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Ceilings & walls", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Floors", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Stick-framed wall /ceiling system", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Wall ceiling Insulated Panel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Building and MEP services", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 480, 60, 4200, "National Embodied Carbon Databook v1.00 2026 - Windows, floors, ceilings and partitions"),
    ("Australia", "Escalator", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 8300, "National Embodied Carbon Databook v1.00 2026 - Globally manufactured"),
    ("Australia", "Lifts", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 8300, "National Embodied Carbon Databook v1.00 2026 - Globally manufactured"),
    ("Australia", "Photovoltaic panels", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 2800, "National Embodied Carbon Databook v1.00 2026 - Nationally and NZ manufactured (interstate)"),
    ("Australia", "Concrete components", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 350, None, 3400, "National Embodied Carbon Databook v1.00 2026 - Cement and cementitious materials"),
    ("Australia", "Concrete in-situ", "Concrete Agitator Truck", "Rail, Bulk Transport", "Shipping", 110, None, None, "National Embodied Carbon Databook v1.00 2026 - Concrete (ready-mix)"),
    ("Australia", "Precast concrete", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 30, None, None, "National Embodied Carbon Databook v1.00 2026 - Concrete (precast)"),
    ("Australia", "Masonry", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 110, None, None, "National Embodied Carbon Databook v1.00 2026 - Concrete (ready-mix)"),
    ("Australia", "Paint", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured (general)"),
    ("Australia", "Asphalt", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 80, None, None, "National Embodied Carbon Databook v1.00 2026 - Asphalt"),
    ("Australia", "Bitumen", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 80, None, None, "National Embodied Carbon Databook v1.00 2026 - Asphalt"),
    ("Australia", "Pavers", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 80, None, None, "National Embodied Carbon Databook v1.00 2026 - Asphalt"),
    ("Australia", "Geopolymer pipes", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 2800, "National Embodied Carbon Databook v1.00 2026 - Nationally and NZ manufactured (interstate)"),
    ("Australia", "PE Pipes", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 2800, "National Embodied Carbon Databook v1.00 2026 - Nationally and NZ manufactured (interstate)"),
    ("Australia", "PVC Pipes", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 2800, "National Embodied Carbon Databook v1.00 2026 - Nationally and NZ manufactured (interstate)"),
    ("Australia", "Steel pipes", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 550, None, 2800, "National Embodied Carbon Databook v1.00 2026 - Nationally and NZ manufactured (interstate)"),
    ("Australia", "Rubbers", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured"),
    ("Australia", "Sealants and adhesives", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured"),
    ("Australia", "Thermoplastics", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured"),
    ("Australia", "Cold rolled steel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 130, 1400, 900, "National Embodied Carbon Databook v1.00 2026 - Steel \u2013 Structural Elements"),
    ("Australia", "Hot rolled steel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 130, 1400, 900, "National Embodied Carbon Databook v1.00 2026 - Steel \u2013 Structural Elements"),
    ("Australia", "Reinforcing steel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 1200, None, 2500, "National Embodied Carbon Databook v1.00 2026 - Steel Reinforcement"),
    ("Australia", "Steel wire", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 1200, None, 2500, "National Embodied Carbon Databook v1.00 2026 - Steel Reinforcement"),
    ("Australia", "Stainless steel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 1200, None, 2500, "National Embodied Carbon Databook v1.00 2026 - Steel Reinforcement"),
    ("Australia", "Timber (engineered)", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 380, None, 4700, "National Embodied Carbon Databook v1.00 2026"),
    ("Australia", "Timber (sawn)", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 330, None, 800, "National Embodied Carbon Databook v1.00 2026 - Timber (engineered)"),
    ("Australia", "Waste to recycling", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Transport of waste to treatment"),
    ("Australia", "Waste to landfill", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Transport of waste to treatment"),
    # New Zealand
    ("New Zealand", "Waste to landfill with gas recovery", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Transport of waste to treatment as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Waste to landfill without gas recovery", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Transport of waste to treatment as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Non municipal waste", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Transport of waste to treatment as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Concrete In-situ", "Concrete Agitator Truck", "Rail, Bulk Transport", "Shipping", 20, None, None, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average"),
    ("New Zealand", "Concrete Precast", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 67, None, None, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average"),
    ("New Zealand", "Cement", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 481, None, 5003, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of cement products"),
    ("New Zealand", "Lime", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 40, None, None, "National Embodied Carbon Databook v1.00 2026 - Aggregates as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Other Metal", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 587, None, 3087, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of aluminium and copper products"),
    ("New Zealand", "Steel", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 486, None, 2993, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of steel products"),
    ("New Zealand", "Aggregate", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 40, None, None, "National Embodied Carbon Databook v1.00 2026 - Aggregates as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Asphalt", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 100, None, 25000, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average"),
    ("New Zealand", "Bitumen", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 80, None, None, "National Embodied Carbon Databook v1.00 2026 - Asphalt as a proxy in the absence of data from BRANZ"),
    ("New Zealand", "Cable", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured (general) in the absence of data from BRANZ"),
    ("New Zealand", "Glass", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 308, None, 6458, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of glass products"),
    ("New Zealand", "Plastic", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 392, None, 7416, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of plastic products"),
    ("New Zealand", "Wood", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 464, None, 5383, "Building Research Association of New Zealand (BRANZ) NZ_WBWLF_-_Module_A4_transport_datasheet_v1 national average of wood and timber products"),
    ("New Zealand", "Paint", "Articulated Truck", "Rail, Bulk Transport", "Shipping", 50, None, None, "National Embodied Carbon Databook v1.00 2026 - Locally manufactured (general) in the absence of data from BRANZ"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Resolve unit id ────────────────────────────────────────────────────────
    km_row = conn.execute(text("SELECT id FROM units WHERE code = 'km'")).fetchone()
    km_unit_id = str(km_row[0]) if km_row else None

    # ── Resolve jurisdiction ids ───────────────────────────────────────────────
    jur_rows = conn.execute(text("SELECT id, name FROM jurisdictions")).fetchall()
    jur_map = {name: str(id_) for id_, name in jur_rows}

    # ── Resolve emissions_category ids ────────────────────────────────────────
    cat_rows = conn.execute(text("SELECT id, name FROM emissions_categories")).fetchall()
    cat_map = {name: str(id_) for id_, name in cat_rows}

    # ── Wipe existing data ─────────────────────────────────────────────────────
    conn.execute(text("DELETE FROM default_transport_distances"))

    # ── Insert new rows ────────────────────────────────────────────────────────
    skipped = []
    inserted = 0
    for (jur_name, cat_name, truck_mode, rail_mode, sea_mode,
         truck_km, rail_km, sea_km, source) in _ROWS:

        jur_id = jur_map.get(jur_name)
        cat_id = cat_map.get(cat_name)

        if jur_id is None:
            skipped.append(f"unknown jurisdiction '{jur_name}'")
            continue
        if cat_id is None:
            skipped.append(f"unknown emissions category '{cat_name}' (jur={jur_name})")
            continue

        conn.execute(text("""
            INSERT INTO default_transport_distances
                (jurisdiction_id, emissions_category_id,
                 truck_distance, rail_distance, sea_distance, distance_unit_id,
                 truck_transport_mode, rail_transport_mode, sea_transport_mode,
                 source)
            VALUES
                (:jur, :cat,
                 :truck_dist, :rail_dist, :sea_dist, :unit_id,
                 :truck_mode, :rail_mode, :sea_mode,
                 :source)
        """), {
            "jur": jur_id,
            "cat": cat_id,
            "truck_dist": truck_km,
            "rail_dist": rail_km,
            "sea_dist": sea_km,
            "unit_id": km_unit_id,
            "truck_mode": truck_mode,
            "rail_mode": rail_mode,
            "sea_mode": sea_mode,
            "source": source,
        })
        inserted += 1

    if skipped:
        print(f"  [transport_distances_v2] WARNING — skipped {len(skipped)} row(s):")
        for msg in skipped:
            print(f"    - {msg}")

    print(f"  [transport_distances_v2] {inserted} rows inserted.")


def downgrade() -> None:
    # No backward compatibility — just wipe on downgrade.
    op.get_bind().execute(text("DELETE FROM default_transport_distances"))
