"""Store annual road user emissions in the shared emissions result ledger.

Revision ID: er03_annual_road_user_results
Revises: er02_result_revision
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "er03_annual_road_user_results"
down_revision = "er02_result_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("emissions_results", "activity_data_id", nullable=True)
    op.add_column(
        "emissions_results",
        sa.Column("project_option_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "emissions_results",
        sa.Column("assessment_year", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_emissions_results_project_option_id_project_options",
        "emissions_results",
        "project_options",
        ["project_option_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "uq_emissions_results_option_year_key",
        "emissions_results",
        ["project_option_id", "assessment_year", "value_key"],
        unique=True,
        postgresql_where=sa.text("assessment_year IS NOT NULL"),
    )

    # Backfill the existing annual road outputs. These ledger facts deliberately
    # have no activity_data_id: the specialist tables hold option/year/type
    # results, while the input rows may be edited or split independently.
    op.execute(sa.text("""
        DO $$ BEGIN
          IF to_regclass('public.user_emissions_nz_results') IS NOT NULL THEN
            INSERT INTO emissions_results
              (project_id, project_stage_instance_id, project_option_id, assessment_year,
               activity_data_id, value_key, lifecycle_module_code, source_category,
               accounting_basis, reporting_measure, is_supplementary, value)
            SELECT r.project_id, r.project_stage_instance_id, r.project_option_id, r.assessment_year,
                   NULL, v.key, 'B8', 'Road user transport', 'common', 'actual', FALSE, v.value
            FROM user_emissions_nz_results r
            CROSS JOIN LATERAL (VALUES
              ('b8_road_general_fleet', r.general_fleet_emissions_tco2e),
              ('b8_road_light_vehicle', r.light_vehicle_emissions_tco2e),
              ('b8_road_heavy_vehicle', r.heavy_vehicle_emissions_tco2e),
              ('b8_road_bus', r.bus_emissions_tco2e)
            ) v(key, value)
            WHERE v.value IS NOT NULL
            ON CONFLICT (project_option_id, assessment_year, value_key)
              WHERE assessment_year IS NOT NULL
            DO UPDATE SET value = EXCLUDED.value;
          END IF;

          IF to_regclass('public.user_emissions_aus_small_results') IS NOT NULL THEN
            INSERT INTO emissions_results
              (project_id, project_stage_instance_id, project_option_id, assessment_year,
               activity_data_id, value_key, lifecycle_module_code, source_category,
               accounting_basis, reporting_measure, is_supplementary, value)
            SELECT r.project_id, r.project_stage_instance_id, r.project_option_id, r.assessment_year,
                   NULL, v.key, 'B8', 'Road user transport', 'common', 'actual', FALSE, v.value
            FROM user_emissions_aus_small_results r
            CROSS JOIN LATERAL (VALUES
              ('b8_road_light_vehicle', r.light_vehicle_emissions_tco2e),
              ('b8_road_medium_vehicle', r.medium_vehicle_emissions_tco2e),
              ('b8_road_heavy_vehicle', r.heavy_vehicle_emissions_tco2e),
              ('b8_road_super_heavy_vehicle', r.super_heavy_vehicle_emissions_tco2e)
            ) v(key, value)
            WHERE v.value IS NOT NULL
            ON CONFLICT (project_option_id, assessment_year, value_key)
              WHERE assessment_year IS NOT NULL
            DO UPDATE SET value = EXCLUDED.value;
          END IF;

          IF to_regclass('public.user_emissions_nz_large_road_results') IS NOT NULL THEN
            INSERT INTO emissions_results
              (project_id, project_stage_instance_id, project_option_id, assessment_year,
               activity_data_id, value_key, lifecycle_module_code, source_category,
               accounting_basis, reporting_measure, is_supplementary, value)
            SELECT r.project_id, r.project_stage_instance_id, r.project_option_id, r.assessment_year,
                   NULL, 'b8_road_' || regexp_replace(lower(r.vehicle_type), '[^a-z0-9]+', '_', 'g'),
                   'B8', 'Road user transport', 'common', 'actual', FALSE, r.emissions_tco2e
            FROM user_emissions_nz_large_road_results r
            WHERE r.emissions_tco2e IS NOT NULL
            ON CONFLICT (project_option_id, assessment_year, value_key)
              WHERE assessment_year IS NOT NULL
            DO UPDATE SET value = EXCLUDED.value;
          END IF;

          IF to_regclass('public.user_emissions_aus_large_road_results') IS NOT NULL THEN
            INSERT INTO emissions_results
              (project_id, project_stage_instance_id, project_option_id, assessment_year,
               activity_data_id, value_key, lifecycle_module_code, source_category,
               accounting_basis, reporting_measure, is_supplementary, value)
            SELECT r.project_id, r.project_stage_instance_id, r.project_option_id, r.assessment_year,
                   NULL, 'b8_road_' || regexp_replace(lower(r.vehicle_type), '[^a-z0-9]+', '_', 'g'),
                   'B8', 'Road user transport', 'common', 'actual', FALSE, r.emissions_tco2e
            FROM user_emissions_aus_large_road_results r
            WHERE r.emissions_tco2e IS NOT NULL
            ON CONFLICT (project_option_id, assessment_year, value_key)
              WHERE assessment_year IS NOT NULL
            DO UPDATE SET value = EXCLUDED.value;
          END IF;
        END $$;
    """))
    op.execute(sa.text("""
        INSERT INTO emissions_results
          (project_id, project_stage_instance_id, project_option_id, assessment_year,
           activity_data_id, value_key, lifecycle_module_code, source_category,
           accounting_basis, reporting_measure, is_supplementary, value)
        SELECT ad.project_id, ad.project_stage_instance_id, ad.project_option_id,
               EXTRACT(YEAR FROM p.commencement_of_operations)::integer + years.year_offset,
               NULL, 'b8_rail_' || replace(ad.id::text, '-', '') || '_' ||
                   (EXTRACT(YEAR FROM p.commencement_of_operations)::integer + years.year_offset)::text, 'B8',
               'Rail user transport', 'common', 'actual', FALSE,
               COALESCE(
                   NULLIF(ad.extra_fields->>'emissions_annual_tco2e', '')::numeric,
                   er.value / GREATEST(COALESCE(p.operational_life_years, 1), 1)
               )
        FROM activity_data ad
        JOIN project p ON p.id = ad.project_id
        JOIN emissions_results er ON er.activity_data_id = ad.id
        CROSS JOIN LATERAL generate_series(
            0, GREATEST(COALESCE(p.operational_life_years, 1), 1) - 1
        ) AS years(year_offset)
        WHERE ad.ui_table_key IN ('railUsers', 'largeRailUsers')
          AND ad.project_option_id IS NOT NULL
          AND p.commencement_of_operations IS NOT NULL
          AND er.lifecycle_module_code = 'B8'
          AND er.reporting_measure = 'actual'
          AND er.is_supplementary IS FALSE
        ON CONFLICT (project_option_id, assessment_year, value_key)
          WHERE assessment_year IS NOT NULL
        DO UPDATE SET value = EXCLUDED.value;
    """))
    op.execute(sa.text("""
        UPDATE emissions_results er
        SET dataset_revision_id = (
            SELECT pdr.dataset_revision_id
            FROM project_dataset_revisions pdr
            WHERE pdr.project_id = er.project_id
            ORDER BY pdr.applied_at DESC, pdr.id DESC
            LIMIT 1
        )
        WHERE er.assessment_year IS NOT NULL
    """))
    op.execute(sa.text("""
        CREATE FUNCTION delete_annual_rail_result_facts() RETURNS trigger AS $$
        BEGIN
          DELETE FROM emissions_results
          WHERE activity_data_id IS NULL
            AND assessment_year IS NOT NULL
            AND value_key ~ ('^b8_rail_' || replace(OLD.id::text, '-', '') || '_[0-9]+$');
          RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_delete_annual_rail_result_facts
        BEFORE DELETE ON activity_data
        FOR EACH ROW EXECUTE FUNCTION delete_annual_rail_result_facts();
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_delete_annual_rail_result_facts ON activity_data"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS delete_annual_rail_result_facts()"))
    op.execute(sa.text("DELETE FROM emissions_results WHERE assessment_year IS NOT NULL"))
    op.drop_index("uq_emissions_results_option_year_key", table_name="emissions_results")
    op.drop_constraint(
        "fk_emissions_results_project_option_id_project_options",
        "emissions_results",
        type_="foreignkey",
    )
    op.drop_column("emissions_results", "assessment_year")
    op.drop_column("emissions_results", "project_option_id")
    op.alter_column("emissions_results", "activity_data_id", nullable=False)
