"""
routers/org_dashboard_hotspots.py

Organisational Dashboard — Materials Hotspots

Aggregates A1-A4 materials emissions across all projects belonging to the given
organisation, with optional filters by project class, program name, and
submission stage.

Two endpoints:
  GET /api/org-dashboard/hotspots/summary  — emissions aggregated by sub-category
  GET /api/org-dashboard/hotspots/detail   — row-level breakdown (includes project info)
"""

import re
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/org-dashboard/hotspots",
    tags=["Org Dashboard - Materials Hotspots"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgHotspotsSummaryRow(DashboardBase):
    sub_category: str
    actual_tco2e: Decimal
    mitigation_tco2e: Decimal
    base_case_tco2e: Decimal


class OrgHotspotsSummaryResponse(DashboardBase):
    rows: List[OrgHotspotsSummaryRow]
    total_actual_tco2e: Decimal
    total_mitigation_tco2e: Decimal
    total_base_case_tco2e: Decimal


class OrgHotspotsDetailRow(DashboardBase):
    project_id: UUID
    project_name: str
    data_source: str
    row_type: str
    sub_category: str
    item: Optional[str]
    actual_tco2e: Decimal
    mitigation_tco2e: Decimal
    base_case_tco2e: Decimal
    unit: Optional[str]


class OrgHotspotsDetailResponse(DashboardBase):
    rows: List[OrgHotspotsDetailRow]


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "project_type_id": str(project_type_id) if project_type_id else None,
        "project_typecast_id": str(project_typecast_id) if project_typecast_id else None,
        "project_option_id": None,
        "submission_period_id": None,
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


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SUMMARY_SQL = text("""
WITH
eligible_projects AS (
    -- All (project, stage_instance) pairs belonging to the given organisation,
    -- filtered by optional project_class, program_name, stage.
    SELECT DISTINCT
        p.id   AS project_id,
        psi.id AS stage_instance_id
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
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
),

-- 1a. Grade 3/4 — actual rows
grade34_actual AS (
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)') AS sub_category,
        SUM(COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)) AS actual_tco2e,
        0::numeric                                                                                 AS mitigation_tco2e
    FROM activity_data ad
    LEFT JOIN emissions_results er_a1a3
        ON er_a1a3.activity_data_id = ad.id
        AND er_a1a3.value_key = 'A1-A3'
        AND NOT er_a1a3.is_supplementary
    LEFT JOIN emissions_results er_a4
        ON er_a4.activity_data_id = ad.id
        AND er_a4.value_key = 'A4'
        AND NOT er_a4.is_supplementary
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'opEnergyDetailed')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
    GROUP BY ad.extra_fields->>'emissions_subcategory'
),

-- 1b. Grade 3/4 — mitigation rows
grade34_mit AS (
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)') AS sub_category,
        0::numeric                                                                                 AS actual_tco2e,
        SUM(COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)) AS mitigation_tco2e
    FROM activity_data ad
    LEFT JOIN emissions_results er_a1a3
        ON er_a1a3.activity_data_id = ad.id
        AND er_a1a3.value_key = 'A1-A3'
        AND NOT er_a1a3.is_supplementary
    LEFT JOIN emissions_results er_a4
        ON er_a4.activity_data_id = ad.id
        AND er_a4.value_key = 'A4'
        AND NOT er_a4.is_supplementary
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN (
            'bcDetailedLevel-mitigation',
            'replDetailed-mitigation',
            'opEnergyDetailed-mitigation'
        )
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
    GROUP BY ad.extra_fields->>'emissions_subcategory'
),

-- 2a. Concrete Registers — actual rows
concrete_actual AS (
    SELECT
        'Concrete'::text AS sub_category,
        SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0)) AS actual_tco2e,
        0::numeric                                                                       AS mitigation_tco2e
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

-- 2b. Concrete Registers — mitigation rows
concrete_mit AS (
    SELECT
        'Concrete'::text AS sub_category,
        0::numeric                                                                       AS actual_tco2e,
        SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0)) AS mitigation_tco2e
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('concreteRegSimplified-mitigation', 'concreteRegDetailed-mitigation')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

-- 3. Shortcut — IS Materials (non-maintenance rows)
is_materials AS (
    SELECT
        'Other shortcuts'::text AS sub_category,
        SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0))  AS actual_tco2e,
        GREATEST(0,
            SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure IN ('actual', 'baseline_adjustment') AND er.is_supplementary IS FALSE), 0)) -
            SUM(COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0))
        )                                                                        AS mitigation_tco2e
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'shortcutIsMaterials'
      AND (ad.extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

-- 4. Shortcut — SAT4P (A1-A4 sources only)
sat4p AS (
    SELECT
        'Other shortcuts'::text AS sub_category,
        SUM(
            COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0)
        )                       AS actual_tco2e,
        SUM(COALESCE((
            SELECT SUM(er.value)
            FROM emissions_results er
            WHERE er.activity_data_id = ad.id
              AND er.reporting_measure = 'baseline_adjustment'
              AND er.is_supplementary IS FALSE
        ), 0))                   AS mitigation_tco2e
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'shortcutSat4p'
      AND ad.extra_fields->>'source' IN (
            'Construction materials',
            'Transport (construction materials)'
        )
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
),

all_sources AS (
    SELECT * FROM grade34_actual
    UNION ALL SELECT * FROM grade34_mit
    UNION ALL SELECT * FROM concrete_actual
    UNION ALL SELECT * FROM concrete_mit
    UNION ALL SELECT * FROM is_materials
    UNION ALL SELECT * FROM sat4p
)

SELECT
    sub_category,
    SUM(actual_tco2e)                         AS actual_tco2e,
    SUM(mitigation_tco2e)                     AS mitigation_tco2e,
    SUM(actual_tco2e) + SUM(mitigation_tco2e) AS base_case_tco2e
FROM all_sources
WHERE sub_category IS NOT NULL
GROUP BY sub_category
HAVING SUM(actual_tco2e) > 0 OR SUM(mitigation_tco2e) > 0
ORDER BY (SUM(actual_tco2e) + SUM(mitigation_tco2e)) DESC NULLS LAST
""")

_DETAIL_SQL = text("""
WITH
eligible_projects AS (
    SELECT DISTINCT
        p.id           AS project_id,
        p.project_name AS project_name,
        psi.id         AS stage_instance_id
    FROM project p
    JOIN project_stage_instances psi ON psi.project_id = p.id
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

-- 1a. Grade 3/4 — actual rows
SELECT
    ep.project_id                                                                    AS project_id,
    ep.project_name                                                                  AS project_name,
    'Grade 3/4 Detailed'::text                                                       AS data_source,
    'actual'::text                                                                   AS row_type,
    COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)')
                                                                                     AS sub_category,
    COALESCE(ad.extra_fields->>'emissions_source', '(unspecified)')                  AS item,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                           AS actual_tco2e,
    0::numeric                                                                       AS mitigation_tco2e,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                           AS base_case_tco2e,
    ad.extra_fields->>'unit_code'                                                    AS unit
FROM activity_data ad
LEFT JOIN emissions_results er_a1a3
    ON er_a1a3.activity_data_id = ad.id
    AND er_a1a3.value_key = 'A1-A3'
    AND NOT er_a1a3.is_supplementary
LEFT JOIN emissions_results er_a4
    ON er_a4.activity_data_id = ad.id
    AND er_a4.value_key = 'A4'
    AND NOT er_a4.is_supplementary
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'opEnergyDetailed')
  AND ad.extra_fields->>'emissions_category' = 'Materials'
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- 1b. Grade 3/4 — mitigation rows
SELECT
    ep.project_id,
    ep.project_name,
    'Grade 3/4 Detailed'::text,
    'mitigation'::text,
    COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)'),
    COALESCE(ad.extra_fields->>'emissions_source', '(unspecified)'),
    0::numeric,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0),
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0),
    ad.extra_fields->>'unit_code'
FROM activity_data ad
LEFT JOIN emissions_results er_a1a3
    ON er_a1a3.activity_data_id = ad.id
    AND er_a1a3.value_key = 'A1-A3'
    AND NOT er_a1a3.is_supplementary
LEFT JOIN emissions_results er_a4
    ON er_a4.activity_data_id = ad.id
    AND er_a4.value_key = 'A4'
    AND NOT er_a4.is_supplementary
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN (
        'bcDetailedLevel-mitigation',
        'replDetailed-mitigation',
        'opEnergyDetailed-mitigation'
    )
  AND ad.extra_fields->>'emissions_category' = 'Materials'
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- 2a. Concrete Registers — actual rows
SELECT
    ep.project_id,
    ep.project_name,
    'Concrete Register'::text,
    'actual'::text,
    'Concrete'::text,
    COALESCE(ad.extra_fields->>'component_type', '(unspecified)'),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0),
    0::numeric,
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0),
    ad.extra_fields->>'unit_code'
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- 2b. Concrete Registers — mitigation rows
SELECT
    ep.project_id,
    ep.project_name,
    'Concrete Register'::text,
    'mitigation'::text,
    'Concrete'::text,
    COALESCE(ad.extra_fields->>'component_type', '(unspecified)'),
    0::numeric,
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = CASE WHEN ad.project_mitigation_id IS NOT NULL OR ad.ui_table_key LIKE '%-mitigation%' THEN 'mitigation' ELSE 'actual' END AND er.is_supplementary IS FALSE), 0),
    ad.extra_fields->>'unit_code'
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('concreteRegSimplified-mitigation', 'concreteRegDetailed-mitigation')
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- 3. Shortcut — IS Materials (non-maintenance rows)
SELECT
    ep.project_id,
    ep.project_name,
    'IS Materials (Shortcut)'::text,
    'actual'::text,
    'Other shortcuts'::text,
    COALESCE(
        NULLIF(ad.extra_fields->>'component_type', ''),
        NULLIF(ad.extra_fields->>'sub_component_type', ''),
        '(unspecified)'
    ),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0),
    GREATEST(0,
        COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure IN ('actual', 'baseline_adjustment') AND er.is_supplementary IS FALSE), 0) -
        COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0)
    ),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure IN ('actual', 'baseline_adjustment') AND er.is_supplementary IS FALSE), 0),
    NULL::text
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key = 'shortcutIsMaterials'
  AND (ad.extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- 4. Shortcut — SAT4P (A1-A4 sources only)
SELECT
    ep.project_id,
    ep.project_name,
    'SAT4P (Shortcut)'::text,
    'actual'::text,
    'Other shortcuts'::text,
    ad.extra_fields->>'source',
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'actual' AND er.is_supplementary IS FALSE), 0),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure = 'baseline_adjustment' AND er.is_supplementary IS FALSE), 0),
    COALESCE((SELECT SUM(er.value) FROM emissions_results er WHERE er.activity_data_id = ad.id AND er.reporting_measure IN ('actual', 'baseline_adjustment') AND er.is_supplementary IS FALSE), 0),
    NULL::text
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key = 'shortcutSat4p'
  AND ad.extra_fields->>'source' IN (
        'Construction materials',
        'Transport (construction materials)'
    )
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

ORDER BY sub_category, data_source, item
""")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=OrgHotspotsSummaryResponse)
async def org_hotspots_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns materials emissions aggregated by sub-category across all org projects."""
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_SUMMARY_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    summary_rows = [OrgHotspotsSummaryRow(**dict(r)) for r in rows]
    return OrgHotspotsSummaryResponse(
        rows=summary_rows,
        total_actual_tco2e=sum((r.actual_tco2e for r in summary_rows), Decimal(0)),
        total_mitigation_tco2e=sum((r.mitigation_tco2e for r in summary_rows), Decimal(0)),
        total_base_case_tco2e=sum((r.base_case_tco2e for r in summary_rows), Decimal(0)),
    )


@router.get("/detail", response_model=OrgHotspotsDetailResponse)
async def org_hotspots_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns every individual materials hotspots row across all org projects."""
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_DETAIL_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    return OrgHotspotsDetailResponse(rows=[OrgHotspotsDetailRow(**dict(r)) for r in rows])
