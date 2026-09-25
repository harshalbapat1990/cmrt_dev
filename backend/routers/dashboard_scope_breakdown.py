from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/dashboard/scope-breakdown",
    tags=["Dashboard - Scope Breakdown"],
)


class ScopeBreakdownRow(DashboardBase):
    scope: str
    baseline_construction: Decimal
    baseline_operations: Decimal
    baseline_lifecycle: Decimal
    actual_construction: Decimal
    actual_operations: Decimal
    actual_lifecycle: Decimal


class ScopeBreakdownResponse(DashboardBase):
    rows: List[ScopeBreakdownRow]


_SCOPE1_CONSTRUCTION_SQL = text("""
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = 'scope1'
    AND er.is_supplementary = TRUE
WHERE ad.project_id                = :project_id
  AND ad.project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
""")

_SCOPE2_CONSTRUCTION_SQL = text("""
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = CASE WHEN :elec_method = 'market' THEN 'scope2_market' ELSE 'scope2_location' END
    AND er.is_supplementary = TRUE
WHERE ad.project_id                = :project_id
  AND ad.project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'electricity'
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
""")

_SCOPE1_OPERATIONS_SQL = text("""
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = 'scope1'
    AND er.is_supplementary = TRUE
WHERE ad.project_id                = :project_id
  AND ad.project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('replDetailed', 'opEnergyDetailed', 'useB1G2', 'useB1G3')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
""")

_SCOPE2_OPERATIONS_SQL = text("""
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = CASE WHEN :elec_method = 'market' THEN 'scope2_market' ELSE 'scope2_location' END
    AND er.is_supplementary = TRUE
WHERE ad.project_id                = :project_id
  AND ad.project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('opEnergyElectricity', 'opEnergy')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
""")

_TOTAL_CONSTRUCTION_SQL = text("""
WITH
-- Grade 2 component splits
g2_a1a3 AS (
    SELECT
        CASE
            WHEN g2."Product Stage (A1-3) (tCO2e/UoM)" IS NOT NULL
            THEN COALESCE(g2."Product Stage (A1-3) (tCO2e/UoM)", 0) * ad.quantity
            ELSE COALESCE(NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
        END AS val
    FROM activity_data ad
    LEFT JOIN v_grade2_component_level g2
        ON  g2."Jurisdiction"           = :jurisdiction
        AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '__no_match__')
        AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
        AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g2_a4 AS (
    SELECT
        CASE
            WHEN g2."Transport Stage (A4) (tCO2e/UoM)" IS NOT NULL
            THEN COALESCE(g2."Transport Stage (A4) (tCO2e/UoM)", 0) * ad.quantity
            ELSE 0
        END AS val
    FROM activity_data ad
    LEFT JOIN v_grade2_component_level g2
        ON  g2."Jurisdiction"           = :jurisdiction
        AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '__no_match__')
        AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
        AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g2_a5 AS (
    SELECT
        CASE
            WHEN g2."Construction Stage (A5) (tCO2e/UoM)" IS NOT NULL
            THEN COALESCE(g2."Construction Stage (A5) (tCO2e/UoM)", 0) * ad.quantity
            ELSE 0
        END AS val
    FROM activity_data ad
    LEFT JOIN v_grade2_component_level g2
        ON  g2."Jurisdiction"           = :jurisdiction
        AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '__no_match__')
        AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
        AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
-- Grade 3/4 Materials A1-A3 and A4 from emissions_results
g34_mat_a1a3 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    LEFT JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A1-A3'
        AND NOT er.is_supplementary
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g34_mat_a4 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    LEFT JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A4'
        AND NOT er.is_supplementary
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
-- Grade 3/4 A5 non-Materials from emissions_results (includes recurringG3)
g34_nonmat_a5 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A5'
        AND NOT er.is_supplementary
    WHERE ad.project_id                = :project_id
      AND ad.project_stage_instance_id = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND COALESCE(ad.extra_fields->>'emissions_category', '') NOT IN ('Materials', 'Offset')
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
)
SELECT
    -- Grade 1 (from emissions_results non-supplementary rows)
    (SELECT COALESCE(SUM(er.value), 0)
     FROM activity_data ad
     JOIN emissions_results er
         ON  er.activity_data_id = ad.id
         AND NOT er.is_supplementary
     WHERE ad.project_id = :project_id AND ad.project_stage_instance_id = :stage_instance_id
       AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
       AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
       AND ad.ui_table_key = 'asset'
       AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    -- Grade 2 component (A1-A3 + A4 + A5)
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a1a3)
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a4)
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a5)
    -- Grade 3/4 Materials (A1-A3 + A4)
    + (SELECT val FROM g34_mat_a1a3)
    + (SELECT val FROM g34_mat_a4)
    -- Grade 3/4 non-Materials A5
    + (SELECT val FROM g34_nonmat_a5)
    -- Concrete (A1-A3 + A4 from emissions_results)
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND er.value_key IN ('A1-A3', 'A4')
           AND NOT er.is_supplementary
       WHERE ad.project_id = :project_id AND ad.project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    -- Electricity (construction)
    + (SELECT COALESCE(SUM(
           CASE WHEN :elec_method = 'market'
                THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
                ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
           END), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key = 'electricity'
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    -- Shortcut IS Materials (A1-A3 from emissions_results; maintenance rows are excluded by bridge)
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND er.value_key = 'A1-A3'
           AND NOT er.is_supplementary
       WHERE ad.project_id = :project_id AND ad.project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'shortcutIsMaterials'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    -- Shortcut SAT4P
    + (SELECT COALESCE(SUM(
           COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
           COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key = 'shortcutSat4p'
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    AS total_construction
""")

_TOTAL_OPERATIONS_SQL = text("""
SELECT
    -- B1 (Use: useB1G2 fugitive gases + useB1G3 grade3 use phase, from emissions_results)
    (SELECT COALESCE(SUM(er.value), 0)
     FROM activity_data ad
     JOIN emissions_results er
         ON  er.activity_data_id = ad.id
         AND er.value_key = 'B1'
         AND NOT er.is_supplementary
     WHERE ad.project_id = :project_id AND ad.project_stage_instance_id = :stage_instance_id
       AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
       AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
       AND ad.ui_table_key IN ('useB1G2', 'useB1G3')
       AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    -- B2-B5 (Maintenance / Replacement / Refurbishment)
    + (SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key IN ('componentRepl', 'refurbishment', 'replDetailed')
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    -- B6 opEnergy (location: primary B6 row; market: sum scope2_market + scope3_market supplementary)
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND (
               (:elec_method != 'market' AND er.value_key = 'B6' AND NOT er.is_supplementary)
               OR (:elec_method = 'market' AND er.value_key IN ('scope2_market', 'scope3_market') AND er.is_supplementary)
           )
       WHERE ad.project_id = :project_id AND ad.project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'opEnergy'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    -- B6 opEnergyDetailed non-Water
    + (SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key = 'opEnergyDetailed'
         AND COALESCE(extra_fields->>'emissions_category', '') != 'Water'
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    -- B6 opEnergyElectricity (location/market_based_tco2e)
    + (SELECT COALESCE(SUM(
           CASE WHEN :elec_method = 'market'
                THEN COALESCE(NULLIF(NULLIF(extra_fields->>'market_based_tco2e', ''), '-')::numeric, 0)
                ELSE COALESCE(NULLIF(NULLIF(extra_fields->>'location_based_tco2e', ''), '-')::numeric, 0)
           END), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key = 'opEnergyElectricity'
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    -- B7 (Water)
    + (SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key = 'opEnergyDetailed'
         AND extra_fields->>'emissions_category' = 'Water'
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    -- B8 (Users)
    + (SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)), 0)
       FROM activity_data
       WHERE project_id = :project_id AND project_stage_instance_id = :stage_instance_id
         AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
         AND ui_table_key IN (
             'roadUsers', 'railUsers',
             'largeRoadUsers', 'largeRoadParams', 'largeRailUsers'
         )
         AND (:actual_only = FALSE OR project_mitigation_id IS NULL))
    AS total_operations
""")

_UPSCALING_CONSTRUCTION_SQL = text("""
SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
FROM activity_data
WHERE project_id = :project_id
  AND project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
  AND ui_table_key = 'completeness'
  AND extra_fields->>'module' IN ('a1_a3', 'a4', 'a5')
""")

_UPSCALING_OPERATIONS_SQL = text("""
SELECT COALESCE(SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'upscaling_adjustment_tco2e', ''), '-')::numeric, 0)), 0) AS val
FROM activity_data
WHERE project_id = :project_id
  AND project_stage_instance_id = :stage_instance_id
  AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
  AND ui_table_key = 'completeness'
  AND extra_fields->>'module' IN ('b1', 'b2_b5', 'b6', 'b7')
""")


async def _scalar(db: AsyncSession, sql, params: dict) -> Decimal:
    result = await db.execute(sql, params)
    row = result.fetchone()
    val = row[0] if row else None
    return Decimal(str(val)) if val is not None else Decimal(0)


@router.get(
    "",
    response_model=ScopeBreakdownResponse,
    summary="Emissions breakdown by GHG scope (1/2/3), lifecycle phase and scenario",
)
async def get_scope_breakdown(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("market", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ScopeBreakdownResponse:
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

    def _base_params(actual_only: bool) -> dict:
        return {
            "project_id":           str(project_id),
            "stage_instance_id":    str(stage_instance_id),
            "elec_method":          elec_method,
            "jurisdiction":         jurisdiction,
            "project_option_id":    str(project_option_id) if project_option_id else None,
            "submission_period_id": str(submission_period_id) if submission_period_id else None,
            "actual_only":          actual_only,
        }

    bl = _base_params(False)
    ac = _base_params(True)

    s1_con_bl = await _scalar(db, _SCOPE1_CONSTRUCTION_SQL, bl)
    s1_con_ac = await _scalar(db, _SCOPE1_CONSTRUCTION_SQL, ac)
    s1_ops_bl = await _scalar(db, _SCOPE1_OPERATIONS_SQL, bl)
    s1_ops_ac = await _scalar(db, _SCOPE1_OPERATIONS_SQL, ac)

    s2_con_bl = await _scalar(db, _SCOPE2_CONSTRUCTION_SQL, bl)
    s2_con_ac = await _scalar(db, _SCOPE2_CONSTRUCTION_SQL, ac)
    s2_ops_bl = await _scalar(db, _SCOPE2_OPERATIONS_SQL, bl)
    s2_ops_ac = await _scalar(db, _SCOPE2_OPERATIONS_SQL, ac)

    tot_con_bl = await _scalar(db, _TOTAL_CONSTRUCTION_SQL, bl)
    tot_con_ac = await _scalar(db, _TOTAL_CONSTRUCTION_SQL, ac)
    tot_ops_bl = await _scalar(db, _TOTAL_OPERATIONS_SQL, bl)
    tot_ops_ac = await _scalar(db, _TOTAL_OPERATIONS_SQL, ac)

    # Completeness upscaling is independent of actual_only (completeness rows have no
    # project_mitigation_id). Construction uplift covers A1-A3/A4/A5; operations covers B1-B7.
    _up_params = {k: v for k, v in bl.items() if k != "actual_only"}
    up_con = await _scalar(db, _UPSCALING_CONSTRUCTION_SQL, _up_params)
    up_ops = await _scalar(db, _UPSCALING_OPERATIONS_SQL, _up_params)
    up_con_bl = up_con
    up_con_ac = up_con
    up_ops_bl = up_ops
    up_ops_ac = up_ops

    s3_con_bl = max(Decimal(0), tot_con_bl - s1_con_bl - s2_con_bl - up_con_bl)
    s3_con_ac = max(Decimal(0), tot_con_ac - s1_con_ac - s2_con_ac - up_con_ac)
    s3_ops_bl = max(Decimal(0), tot_ops_bl - s1_ops_bl - s2_ops_bl - up_ops_bl)
    s3_ops_ac = max(Decimal(0), tot_ops_ac - s1_ops_ac - s2_ops_ac - up_ops_ac)

    def _row(
        scope: str,
        con_bl: Decimal, ops_bl: Decimal,
        con_ac: Decimal, ops_ac: Decimal,
    ) -> ScopeBreakdownRow:
        return ScopeBreakdownRow(
            scope=scope,
            baseline_construction=con_bl,
            baseline_operations=ops_bl,
            baseline_lifecycle=con_bl + ops_bl,
            actual_construction=con_ac,
            actual_operations=ops_ac,
            actual_lifecycle=con_ac + ops_ac,
        )

    rows = [
        _row("1",         s1_con_bl, s1_ops_bl, s1_con_ac, s1_ops_ac),
        _row("2",         s2_con_bl, s2_ops_bl, s2_con_ac, s2_ops_ac),
        _row("3",         s3_con_bl, s3_ops_bl, s3_con_ac, s3_ops_ac),
        _row("upscaling", up_con_bl, up_ops_bl, up_con_ac, up_ops_ac),
        _row("total",     tot_con_bl, tot_ops_bl, tot_con_ac, tot_ops_ac),
    ]

    return ScopeBreakdownResponse(rows=rows)
