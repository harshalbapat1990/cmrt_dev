from decimal import Decimal
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/org-dashboard/scope-breakdown",
    tags=["Org Dashboard - Scope Breakdown"],
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


def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    elec_method: str = "market",
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
    actual_only: bool = False,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "elec_method": elec_method,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
        "project_option_id": str(project_option_id) if project_option_id else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
        "actual_only": actual_only,
    }


def _normalize_enum_filter(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").upper()
    return normalized or None


def _normalize_project_class(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"SMALL", "LARGE", "RECURRING"}:
        return normalized
    return value.strip() if value else None


def _normalize_stage(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_enum_filter(value)
    if normalized in {"BUSINESS_CASE", "DESIGN", "CONSTRUCTION", "RECURRING"}:
        return normalized
    return value.strip() if value else None


def _normalize_elec_method(value: str) -> str:
    normalized = _normalize_enum_filter(value)
    if normalized in {"LOCATION", "LOCATION_BASED"}:
        return "location"
    if normalized in {"MARKET", "MARKET_BASED"}:
        return "market"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="elec_method must be 'location', 'market', 'Location-based', or 'Market-based'",
    )


_ELIGIBLE_PROJECTS_CTE = """
eligible_projects AS (
    SELECT DISTINCT
        p.id                            AS project_id,
        psi.id                          AS stage_instance_id,
        COALESCE(j.name, 'Australia')   AS jurisdiction
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
    LEFT JOIN organization o  ON o.id  = p.proponent_org_id
    LEFT JOIN jurisdictions j ON j.id  = o.jurisdiction_id
    WHERE p.is_active = TRUE
      AND (
          p.proponent_org_id = :org_id
          OR EXISTS (
              SELECT 1 FROM project_organizations po
              WHERE po.project_id = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage AS TEXT) IS NULL OR psi.stage::text = CAST(:stage AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
      AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
)
"""


_SCOPE1_CONSTRUCTION_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = 'scope1'
    AND er.is_supplementary = TRUE
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
"""
)


_SCOPE2_CONSTRUCTION_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = CASE WHEN :elec_method = 'market' THEN 'scope2_market' ELSE 'scope2_location' END
    AND er.is_supplementary = TRUE
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'electricity'
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
"""
)


_SCOPE1_OPERATIONS_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = 'scope1'
    AND er.is_supplementary = TRUE
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('replDetailed', 'opEnergyDetailed', 'useB1G2', 'useB1G3')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
"""
)


_SCOPE2_OPERATIONS_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(er.value), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
JOIN emissions_results er
    ON  er.activity_data_id = ad.id
    AND er.value_key = CASE WHEN :elec_method = 'market' THEN 'scope2_market' ELSE 'scope2_location' END
    AND er.is_supplementary = TRUE
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key IN ('opEnergyElectricity', 'opEnergy')
  AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
"""
)


_TOTAL_CONSTRUCTION_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE},
g2_a1a3 AS (
    SELECT
        COALESCE((SELECT er.value FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.value_key = 'A1-A3' AND er.is_supplementary IS FALSE LIMIT 1), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g2_a4 AS (
    SELECT
        COALESCE((SELECT er.value FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.value_key = 'A4' AND er.is_supplementary IS FALSE LIMIT 1), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g2_a5 AS (
    SELECT
        COALESCE((SELECT er.value FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.value_key = 'A5' AND er.is_supplementary IS FALSE LIMIT 1), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key = 'component'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g34_mat_a1a3 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    LEFT JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A1-A3'
        AND NOT er.is_supplementary
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g34_mat_a4 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    LEFT JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A4'
        AND NOT er.is_supplementary
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
),
g34_nonmat_a5 AS (
    SELECT COALESCE(SUM(er.value), 0) AS val
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    JOIN emissions_results er
        ON  er.activity_data_id = ad.id
        AND er.value_key = 'A5'
        AND NOT er.is_supplementary
    WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
      AND COALESCE(ad.extra_fields->>'emissions_category', '') NOT IN ('Materials', 'Offset')
      AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL)
)
SELECT
    (SELECT COALESCE(SUM(er.value), 0)
     FROM activity_data ad
     JOIN eligible_projects ep
         ON ep.project_id = ad.project_id
        AND ep.stage_instance_id = ad.project_stage_instance_id
     JOIN emissions_results er
         ON  er.activity_data_id = ad.id
         AND NOT er.is_supplementary
     WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
       AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
       AND ad.ui_table_key = 'asset'
       AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a1a3)
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a4)
    + (SELECT COALESCE(SUM(val), 0) FROM g2_a5)
    + (SELECT val FROM g34_mat_a1a3)
    + (SELECT val FROM g34_mat_a4)
    + (SELECT val FROM g34_nonmat_a5)
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND er.value_key IN ('A1-A3', 'A4')
           AND NOT er.is_supplementary
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(
           CASE WHEN :elec_method = 'market'
                THEN COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
                ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
           END), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'electricity'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND er.value_key = 'A1-A3'
           AND NOT er.is_supplementary
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'shortcutIsMaterials'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       JOIN emissions_results er
           ON er.activity_data_id = ad.id
          AND er.reporting_measure = 'actual'
          AND er.is_supplementary IS FALSE
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'shortcutSat4p'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    AS total_construction
"""
)


_TOTAL_OPERATIONS_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT
    (SELECT COALESCE(SUM(er.value), 0)
     FROM activity_data ad
     JOIN eligible_projects ep
         ON ep.project_id = ad.project_id
        AND ep.stage_instance_id = ad.project_stage_instance_id
     JOIN emissions_results er
         ON  er.activity_data_id = ad.id
         AND er.value_key = 'B1'
         AND NOT er.is_supplementary
     WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
       AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
       AND ad.ui_table_key IN ('useB1G2', 'useB1G3')
       AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key IN ('componentRepl', 'refurbishment', 'replDetailed')
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(er.value), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       JOIN emissions_results er
           ON  er.activity_data_id = ad.id
           AND (
               (:elec_method != 'market' AND er.value_key = 'B6' AND NOT er.is_supplementary)
               OR (:elec_method = 'market' AND er.value_key IN ('scope2_market', 'scope3_market') AND er.is_supplementary)
           )
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'opEnergy'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'opEnergyDetailed'
         AND COALESCE(ad.extra_fields->>'emissions_category', '') != 'Water'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(
           CASE WHEN :elec_method = 'market'
                THEN COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
                ELSE COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)
           END), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'opEnergyElectricity'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key = 'opEnergyDetailed'
         AND ad.extra_fields->>'emissions_category' = 'Water'
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    + (SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.is_supplementary IS FALSE AND er.reporting_measure IN ('actual', 'mitigation') AND er.accounting_basis IN ('common', CASE WHEN :elec_method = 'market' THEN 'market' ELSE 'location' END)), 0)), 0)
       FROM activity_data ad
       JOIN eligible_projects ep
           ON ep.project_id = ad.project_id
          AND ep.stage_instance_id = ad.project_stage_instance_id
       WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
         AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
         AND ad.ui_table_key IN (
             'roadUsers', 'railUsers',
             'largeRoadUsers', 'largeRoadParams', 'largeRailUsers'
         )
         AND (:actual_only = FALSE OR ad.project_mitigation_id IS NULL))
    AS total_operations
"""
)


_UPSCALING_CONSTRUCTION_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'baseline_adjustment' AND er.lifecycle_module_code = CASE ad.extra_fields->>'module' WHEN 'a1_a3' THEN 'A1-A3' WHEN 'a4' THEN 'A4' WHEN 'a5' THEN 'A5' WHEN 'b1' THEN 'B1' WHEN 'b2_b5' THEN 'B2-5' WHEN 'b6' THEN 'B6' WHEN 'b7' THEN 'B7' END AND er.is_supplementary IS FALSE), 0)), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'completeness'
  AND ad.extra_fields->>'module' IN ('a1_a3', 'a4', 'a5')
"""
)


_UPSCALING_OPERATIONS_SQL = text(
    f"""
WITH
{_ELIGIBLE_PROJECTS_CTE}
SELECT COALESCE(SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'baseline_adjustment' AND er.lifecycle_module_code = CASE ad.extra_fields->>'module' WHEN 'a1_a3' THEN 'A1-A3' WHEN 'a4' THEN 'A4' WHEN 'a5' THEN 'A5' WHEN 'b1' THEN 'B1' WHEN 'b2_b5' THEN 'B2-5' WHEN 'b6' THEN 'B6' WHEN 'b7' THEN 'B7' END AND er.is_supplementary IS FALSE), 0)), 0) AS val
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'completeness'
  AND ad.extra_fields->>'module' IN ('b1', 'b2_b5', 'b6', 'b7')
"""
)


async def _scalar(db: AsyncSession, sql, params: dict) -> Decimal:
    result = await db.execute(sql, params)
    row = result.fetchone()
    val = row[0] if row else None
    return Decimal(str(val)) if val is not None else Decimal(0)


@router.get(
    "",
    response_model=ScopeBreakdownResponse,
    summary="Org emissions breakdown by GHG scope (1/2/3), lifecycle phase and scenario",
)
async def get_scope_breakdown(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None, description="Filter by project class (e.g. SMALL, LARGE)"),
    program_name: Optional[str] = Query(None, description="Filter by program name (case-insensitive)"),
    stage: Optional[str] = Query(None, description="Filter by stage type (e.g. CONSTRUCTION, RECURRING)"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    elec_method: str = Query("market", description="Electricity accounting: 'location' or 'market'"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ScopeBreakdownResponse:
    normalized_elec_method = _normalize_elec_method(elec_method)

    base_params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        elec_method=normalized_elec_method,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
    )

    bl = {**base_params, "actual_only": False}
    ac = {**base_params, "actual_only": True}

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
        con_bl: Decimal,
        ops_bl: Decimal,
        con_ac: Decimal,
        ops_ac: Decimal,
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
        _row("1", s1_con_bl, s1_ops_bl, s1_con_ac, s1_ops_ac),
        _row("2", s2_con_bl, s2_ops_bl, s2_con_ac, s2_ops_ac),
        _row("3", s3_con_bl, s3_ops_bl, s3_con_ac, s3_ops_ac),
        _row("upscaling", up_con_bl, up_ops_bl, up_con_ac, up_ops_ac),
        _row("total", tot_con_bl, tot_ops_bl, tot_con_ac, tot_ops_ac),
    ]

    return ScopeBreakdownResponse(rows=rows)
