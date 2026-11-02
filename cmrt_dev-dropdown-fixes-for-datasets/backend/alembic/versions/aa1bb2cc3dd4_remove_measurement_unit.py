"""remove_measurement_unit_consolidate_to_units

Revision ID: aa1bb2cc3dd4
Revises: y1z2a3b4c5d6
Create Date: 2026-03-29 00:00:00.000000

Removes the measurement_unit table entirely and points all FK references to
the units table instead. Data is remapped by matching measurement_unit.name = units.code.
Dependent DB views are dropped and recreated using units.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "aa1bb2cc3dd4"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Drop dependent views
    conn.execute(sa.text("DROP VIEW IF EXISTS v_emission_factor_values_pivot"))
    conn.execute(sa.text("DROP VIEW IF EXISTS view_emission_factor_values"))
    conn.execute(sa.text("DROP VIEW IF EXISTS view_emission_factors"))

    # 2. Drop FK constraints referencing measurement_unit first (must come before data remap)
    op.drop_constraint("fk__activity_data__unit_id__measurement_unit", "activity_data", type_="foreignkey")
    op.drop_constraint("emission_entry_measurement_unit_id_fkey", "emission_entry", type_="foreignkey")
    op.drop_constraint("emission_factor_measurement_unit_id_fkey", "emission_factor", type_="foreignkey")
    op.drop_constraint("emission_source_measurement_unit_id_fkey", "emission_source", type_="foreignkey")

    # 3. Remap FK values: measurement_unit.id → units.id (matched by name = code)
    for table in ("emission_source", "emission_factor", "emission_entry"):
        conn.execute(sa.text(f"""
            UPDATE {table} t
            SET measurement_unit_id = u.id
            FROM measurement_unit mu
            JOIN units u ON u.code = mu.name
            WHERE t.measurement_unit_id = mu.id
        """))
    # activity_data.unit_id rows are all NULL — nothing to remap

    # 4. Add FK constraints pointing to units
    op.create_foreign_key(
        "fk__activity_data__unit_id__units", "activity_data", "units",
        ["unit_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk__emission_entry__measurement_unit_id__units", "emission_entry", "units",
        ["measurement_unit_id"], ["id"],
    )
    op.create_foreign_key(
        "fk__emission_factor__measurement_unit_id__units", "emission_factor", "units",
        ["measurement_unit_id"], ["id"],
    )
    op.create_foreign_key(
        "fk__emission_source__measurement_unit_id__units", "emission_source", "units",
        ["measurement_unit_id"], ["id"],
    )

    # 5. Drop measurement_unit table
    op.drop_table("measurement_unit")

    # 6. Recreate views using units table (units.code replaces measurement_unit.name)
    conn.execute(sa.text("""
        CREATE VIEW v_emission_factor_values_pivot AS
        SELECT ef.id AS emission_factor_id,
            ef.emission_source_id,
            es.name AS emission_source_name,
            ef.measurement_unit_id,
            u.code AS measurement_unit_name,
            esc.id AS emissions_sub_category_id,
            esc.name AS emissions_sub_category_name,
            ec.id AS emissions_category_id,
            ec.name AS emissions_category_name,
            MAX(CASE WHEN ev.stage_code = 'A1-3' THEN ev.gwp_kgco2e_per_unit END) AS a1_3,
            MAX(CASE WHEN ev.stage_code = 'A4'   THEN ev.gwp_kgco2e_per_unit END) AS a4,
            MAX(CASE WHEN ev.stage_code = 'A5'   THEN ev.gwp_kgco2e_per_unit END) AS a5,
            MAX(CASE WHEN ev.stage_code = 'B2-5' THEN ev.gwp_kgco2e_per_unit END) AS b2_5,
            MAX(CASE WHEN ev.stage_code = 'C2'   THEN ev.gwp_kgco2e_per_unit END) AS c2,
            MAX(CASE WHEN ev.stage_code = 'C3-4' THEN ev.gwp_kgco2e_per_unit END) AS c3_4
        FROM emission_factor ef
        JOIN emission_source es ON es.id = ef.emission_source_id
        JOIN units u ON u.id = ef.measurement_unit_id
        LEFT JOIN emissions_sub_category esc ON esc.id = es.emissions_sub_category_id
        LEFT JOIN emissions_category ec ON ec.id = esc.emissions_category_id
        LEFT JOIN emission_factor_value ev ON ev.emission_factor_id = ef.id
        GROUP BY ef.id, ef.emission_source_id, es.name, ef.measurement_unit_id, u.code,
                 esc.id, esc.name, ec.id, ec.name
    """))

    conn.execute(sa.text("""
        CREATE VIEW view_emission_factor_values AS
        SELECT ev.id AS emission_factor_value_id,
            ev.emission_factor_id,
            ev.stage_code,
            ev.gwp_kgco2e_per_unit,
            ev.created_on,
            ev.updated_on,
            ef.emission_source_id,
            ef.measurement_unit_id,
            ef.is_active AS factor_is_active,
            es.name AS emission_source_name,
            u.code AS measurement_unit_name,
            esc.id AS emissions_sub_category_id,
            esc.name AS emissions_sub_category_name,
            ec.id AS emissions_category_id,
            ec.name AS emissions_category_name
        FROM emission_factor_value ev
        JOIN emission_factor ef ON ef.id = ev.emission_factor_id
        JOIN emission_source es ON es.id = ef.emission_source_id
        JOIN units u ON u.id = ef.measurement_unit_id
        LEFT JOIN emissions_sub_category esc ON esc.id = es.emissions_sub_category_id
        LEFT JOIN emissions_category ec ON ec.id = esc.emissions_category_id
    """))

    conn.execute(sa.text("""
        CREATE VIEW view_emission_factors AS
        SELECT ef.id AS emission_factor_id,
            ef.is_active,
            ef.created_on,
            ef.updated_on,
            ef.emission_source_id,
            ef.measurement_unit_id,
            es.name AS emission_source_name,
            u.code AS measurement_unit_name,
            esc.id AS emissions_sub_category_id,
            esc.name AS emissions_sub_category_name,
            ec.id AS emissions_category_id,
            ec.name AS emissions_category_name
        FROM emission_factor ef
        JOIN emission_source es ON es.id = ef.emission_source_id
        JOIN units u ON u.id = ef.measurement_unit_id
        LEFT JOIN emissions_sub_category esc ON esc.id = es.emissions_sub_category_id
        LEFT JOIN emissions_category ec ON ec.id = esc.emissions_category_id
    """))


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported: measurement_unit table data cannot be automatically restored."
    )
