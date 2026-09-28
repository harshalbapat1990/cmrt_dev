"""Synchronize annual B8 road calculations into the shared result ledger."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_SMALL_SQL = {
    "nz_small": """
        SELECT r.project_id, r.project_stage_instance_id, r.project_option_id,
               r.assessment_year, v.value_key, v.amount
        FROM user_emissions_nz_results r
        CROSS JOIN LATERAL (VALUES
          ('b8_road_general_fleet', r.general_fleet_emissions_tco2e),
          ('b8_road_light_vehicle', r.light_vehicle_emissions_tco2e),
          ('b8_road_heavy_vehicle', r.heavy_vehicle_emissions_tco2e),
          ('b8_road_bus', r.bus_emissions_tco2e)
        ) v(value_key, amount)
        WHERE r.project_option_id = CAST(:option_id AS uuid) AND v.amount IS NOT NULL
    """,
    "aus_small": """
        SELECT r.project_id, r.project_stage_instance_id, r.project_option_id,
               r.assessment_year, v.value_key, v.amount
        FROM user_emissions_aus_small_results r
        CROSS JOIN LATERAL (VALUES
          ('b8_road_light_vehicle', r.light_vehicle_emissions_tco2e),
          ('b8_road_medium_vehicle', r.medium_vehicle_emissions_tco2e),
          ('b8_road_heavy_vehicle', r.heavy_vehicle_emissions_tco2e),
          ('b8_road_super_heavy_vehicle', r.super_heavy_vehicle_emissions_tco2e)
        ) v(value_key, amount)
        WHERE r.project_option_id = CAST(:option_id AS uuid) AND v.amount IS NOT NULL
    """,
}

_LARGE_SQL = {
    "nz_large": """
        SELECT project_id, project_stage_instance_id, project_option_id,
               assessment_year,
               'b8_road_' || regexp_replace(lower(vehicle_type), '[^a-z0-9]+', '_', 'g') AS value_key,
               emissions_tco2e AS amount
        FROM user_emissions_nz_large_road_results
        WHERE project_option_id = CAST(:option_id AS uuid) AND emissions_tco2e IS NOT NULL
    """,
    "aus_large": """
        SELECT project_id, project_stage_instance_id, project_option_id,
               assessment_year,
               'b8_road_' || regexp_replace(lower(vehicle_type), '[^a-z0-9]+', '_', 'g') AS value_key,
               emissions_tco2e AS amount
        FROM user_emissions_aus_large_road_results
        WHERE project_option_id = CAST(:option_id AS uuid) AND emissions_tco2e IS NOT NULL
    """,
}


async def sync_annual_road_results(
    db: AsyncSession,
    *,
    project_option_id,
    project_class: str,
    is_nz: bool,
) -> None:
    """Replace one option's annual road facts from its specialist calculation rows."""
    source = (
        "nz_large" if is_nz else "aus_large"
    ) if project_class.upper() == "LARGE" else (
        "nz_small" if is_nz else "aus_small"
    )
    source_sql = (_LARGE_SQL if project_class.upper() == "LARGE" else _SMALL_SQL)[source]
    params = {"option_id": str(project_option_id)}

    await db.execute(text("""
        DELETE FROM emissions_results
        WHERE project_option_id = CAST(:option_id AS uuid)
          AND assessment_year IS NOT NULL
          AND value_key ~ '^b8_road_'
    """), params)
    await db.execute(text(f"""
        INSERT INTO emissions_results
          (project_id, project_stage_instance_id, project_option_id, assessment_year, dataset_revision_id,
           activity_data_id, value_key, lifecycle_module_code, source_category,
           accounting_basis, reporting_measure, is_supplementary, value)
        SELECT annual_road.project_id, annual_road.project_stage_instance_id,
               annual_road.project_option_id, annual_road.assessment_year,
               active_revision.dataset_revision_id,
               NULL, annual_road.value_key, 'B8', 'Road user transport', 'common', 'actual', FALSE, annual_road.amount
        FROM ({source_sql}) annual_road
        LEFT JOIN LATERAL (
            SELECT pdr.dataset_revision_id
            FROM project_dataset_revisions pdr
            WHERE pdr.project_id = annual_road.project_id
            ORDER BY pdr.applied_at DESC
            LIMIT 1
        ) active_revision ON TRUE
        ON CONFLICT (project_option_id, assessment_year, value_key)
          WHERE assessment_year IS NOT NULL
        DO UPDATE SET value = EXCLUDED.value,
                      project_id = EXCLUDED.project_id,
                      project_stage_instance_id = EXCLUDED.project_stage_instance_id,
                      dataset_revision_id = EXCLUDED.dataset_revision_id,
                      lifecycle_module_code = 'B8',
                      source_category = 'Road user transport',
                      accounting_basis = 'common',
                      reporting_measure = 'actual'
    """), params)
    await db.flush()
