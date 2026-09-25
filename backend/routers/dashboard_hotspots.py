"""
routers/dashboard_hotspots.py

Dashboard Results API — Materials Hotspots

Returns A1-A4 materials emissions for the "Materials Hotspots" dashboard screen.

Two endpoints
─────────────
  GET /summary   — emissions aggregated by sub-category (drives the chart + left table)
  GET /detail    — row-level breakdown of every contributing entry (drives "View detailed results")

Data sources
─────────────
  1. Grade 3/4 Detailed Level
       Actual rows :  ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'opEnergyDetailed')
                      WHERE extra_fields->>'emissions_category' = 'Materials'
       Mitigation  :  ui_table_key IN ('bcDetailedLevel-mitigation',
                                        'replDetailed-mitigation',
                                        'opEnergyDetailed-mitigation')
                      WHERE extra_fields->>'emissions_category' = 'Materials'

  2. Concrete Registers
       Actual rows :  ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
       Mitigation  :  ui_table_key IN ('concreteRegSimplified-mitigation',
                                        'concreteRegDetailed-mitigation')

  3. Shortcut — IS Materials (non-maintenance rows only)
       ui_table_key = 'shortcutIsMaterials'
       actual      = extra_fields->>'actual_case'
       base        = extra_fields->>'base_case'
       mitigation  = MAX(0, base - actual)

  4. Shortcut — SAT4P (A1-A4 sources only)
       ui_table_key = 'shortcutSat4p'
       source IN ('Construction materials', 'Transport (construction materials)')
       actual      = actual_scope3 + actual_scope4
       base        = base_scope1  + base_scope2
       mitigation  = MAX(0, base - actual)

Field definitions
─────────────────
  actual_tco2e     — current (post-mitigation) emissions
  mitigation_tco2e — savings achieved vs. base case
  base_case_tco2e  — actual + mitigation  (what emissions would be without mitigations)

Query params
────────────
  project_id        UUID  required
  stage_instance_id UUID  required
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session

router = APIRouter(
    prefix="/api/dashboard/hotspots",
    tags=["Dashboard - Materials Hotspots"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class HotspotSummaryRow(DashboardBase):
    """One sub-category row for the summary chart / left table."""
    sub_category: str
    actual_tco2e: Decimal
    mitigation_tco2e: Decimal
    base_case_tco2e: Decimal


class HotspotsSummaryResponse(DashboardBase):
    """
    Aggregated materials emissions by sub-category.

    rows                  → per-subcategory figures (sorted base_case DESC)
    total_actual_tco2e    → sum of actual across all rows
    total_mitigation_tco2e→ sum of mitigation across all rows
    total_base_case_tco2e → sum of base case across all rows
    """
    rows: List[HotspotSummaryRow]
    total_actual_tco2e: Decimal
    total_mitigation_tco2e: Decimal
    total_base_case_tco2e: Decimal


class HotspotDetailRow(DashboardBase):
    """One row for the 'View detailed results' page."""
    data_source: str          # e.g. 'Grade 3/4 Detailed', 'Concrete Register', …
    row_type: str             # 'actual' | 'mitigation'
    sub_category: str
    item: Optional[str]       # material name / emissions source / component
    actual_tco2e: Decimal
    mitigation_tco2e: Decimal
    base_case_tco2e: Decimal
    unit: Optional[str]


class HotspotsDetailResponse(DashboardBase):
    rows: List[HotspotDetailRow]


# ─────────────────────────────────────────────────────────────────────────────
# SQL — summary (one row per sub-category)
# ─────────────────────────────────────────────────────────────────────────────

_SUMMARY_SQL = text("""
WITH
-- 1a. Grade 3/4 — actual rows (A1-A3 + A4 from emissions_results)
grade34_actual AS (
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)') AS sub_category,
        SUM(
            COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)
        ) AS actual_tco2e,
        0::numeric AS mitigation_tco2e
    FROM activity_data ad
    LEFT JOIN emissions_results er_a1a3
        ON er_a1a3.activity_data_id = ad.id
        AND er_a1a3.value_key = 'A1-A3'
        AND NOT er_a1a3.is_supplementary
    LEFT JOIN emissions_results er_a4
        ON er_a4.activity_data_id = ad.id
        AND er_a4.value_key = 'A4'
        AND NOT er_a4.is_supplementary
    WHERE
        ad.project_id                    = :project_id
        AND ad.project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        AND ad.ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'opEnergyDetailed')
        AND ad.extra_fields->>'emissions_category' = 'Materials'
    GROUP BY ad.extra_fields->>'emissions_subcategory'
),

-- 1b. Grade 3/4 — mitigation rows (A1-A3 + A4 from emissions_results)
grade34_mit AS (
    SELECT
        COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)') AS sub_category,
        0::numeric AS actual_tco2e,
        SUM(
            COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)
        ) AS mitigation_tco2e
    FROM activity_data ad
    LEFT JOIN emissions_results er_a1a3
        ON er_a1a3.activity_data_id = ad.id
        AND er_a1a3.value_key = 'A1-A3'
        AND NOT er_a1a3.is_supplementary
    LEFT JOIN emissions_results er_a4
        ON er_a4.activity_data_id = ad.id
        AND er_a4.value_key = 'A4'
        AND NOT er_a4.is_supplementary
    WHERE
        ad.project_id                    = :project_id
        AND ad.project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        AND ad.ui_table_key IN (
            'bcDetailedLevel-mitigation',
            'replDetailed-mitigation',
            'opEnergyDetailed-mitigation'
        )
        AND ad.extra_fields->>'emissions_category' = 'Materials'
    GROUP BY ad.extra_fields->>'emissions_subcategory'
),

-- 2a. Concrete Registers — actual rows
concrete_actual AS (
    SELECT
        'Concrete'::text AS sub_category,
        SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)) AS actual_tco2e,
        0::numeric                                                                    AS mitigation_tco2e
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')
),

-- 2b. Concrete Registers — mitigation rows
concrete_mit AS (
    SELECT
        'Concrete'::text AS sub_category,
        0::numeric                                                                    AS actual_tco2e,
        SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)) AS mitigation_tco2e
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('concreteRegSimplified-mitigation', 'concreteRegDetailed-mitigation')
),

-- 3. Shortcut — IS Materials (non-maintenance rows)
is_materials AS (
    SELECT
        'Other shortcuts'::text AS sub_category,
        SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0))  AS actual_tco2e,
        GREATEST(0,
            SUM(COALESCE(NULLIF(extra_fields->>'base_case',   '')::numeric, 0)) -
            SUM(COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0))
        )                                                                    AS mitigation_tco2e
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key = 'shortcutIsMaterials'
        AND (extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
),

-- 4. Shortcut — SAT4P (A1-A4 sources only)
sat4p AS (
    SELECT
        'Other shortcuts'::text AS sub_category,
        SUM(
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
        )                       AS actual_tco2e,
        GREATEST(0,
            SUM(
                COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
                COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0)
            ) -
            SUM(
                COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
                COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
            )
        )                       AS mitigation_tco2e
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key = 'shortcutSat4p'
        AND extra_fields->>'source' IN (
            'Construction materials',
            'Transport (construction materials)'
        )
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


# ─────────────────────────────────────────────────────────────────────────────
# SQL — detail (one row per activity_data entry)
# ─────────────────────────────────────────────────────────────────────────────

_DETAIL_SQL = text("""
-- 1a. Grade 3/4 — actual rows (A1-A3 + A4 from emissions_results)
SELECT
    'Grade 3/4 Detailed'::text                                                    AS data_source,
    'actual'::text                                                                AS row_type,
    COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)')
                                                                                  AS sub_category,
    COALESCE(ad.extra_fields->>'emissions_source', '(unspecified)')               AS item,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                       AS actual_tco2e,
    0::numeric                                                                    AS mitigation_tco2e,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                       AS base_case_tco2e,
    ad.extra_fields->>'unit_code'                                                AS unit
FROM activity_data ad
LEFT JOIN emissions_results er_a1a3
    ON er_a1a3.activity_data_id = ad.id
    AND er_a1a3.value_key = 'A1-A3'
    AND NOT er_a1a3.is_supplementary
LEFT JOIN emissions_results er_a4
    ON er_a4.activity_data_id = ad.id
    AND er_a4.value_key = 'A4'
    AND NOT er_a4.is_supplementary
WHERE
    ad.project_id                    = :project_id
    AND ad.project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
    AND ad.ui_table_key IN ('bcDetailedLevel', 'replDetailed', 'opEnergyDetailed')
    AND ad.extra_fields->>'emissions_category' = 'Materials'

UNION ALL

-- 1b. Grade 3/4 — mitigation rows (A1-A3 + A4 from emissions_results)
SELECT
    'Grade 3/4 Detailed'::text                                                    AS data_source,
    'mitigation'::text                                                            AS row_type,
    COALESCE(NULLIF(TRIM(ad.extra_fields->>'emissions_subcategory'), ''), '(Other materials)')
                                                                                  AS sub_category,
    COALESCE(ad.extra_fields->>'emissions_source', '(unspecified)')               AS item,
    0::numeric                                                                    AS actual_tco2e,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                       AS mitigation_tco2e,
    COALESCE(er_a1a3.value, 0) + COALESCE(er_a4.value, 0)                       AS base_case_tco2e,
    ad.extra_fields->>'unit_code'                                                AS unit
FROM activity_data ad
LEFT JOIN emissions_results er_a1a3
    ON er_a1a3.activity_data_id = ad.id
    AND er_a1a3.value_key = 'A1-A3'
    AND NOT er_a1a3.is_supplementary
LEFT JOIN emissions_results er_a4
    ON er_a4.activity_data_id = ad.id
    AND er_a4.value_key = 'A4'
    AND NOT er_a4.is_supplementary
WHERE
    ad.project_id                    = :project_id
    AND ad.project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
    AND ad.ui_table_key IN (
        'bcDetailedLevel-mitigation',
        'replDetailed-mitigation',
        'opEnergyDetailed-mitigation'
    )
    AND ad.extra_fields->>'emissions_category' = 'Materials'

UNION ALL

-- 2a. Concrete Registers — actual rows
SELECT
    'Concrete Register'::text                                                     AS data_source,
    'actual'::text                                                                AS row_type,
    'Concrete'::text                                                              AS sub_category,
    COALESCE(extra_fields->>'component_type', '(unspecified)')                    AS item,
    COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)      AS actual_tco2e,
    0::numeric                                                                    AS mitigation_tco2e,
    COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)      AS base_case_tco2e,
    extra_fields->>'unit_code'                                                    AS unit
FROM activity_data
WHERE
    project_id                    = :project_id
    AND project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
    AND ui_table_key IN ('concreteRegSimplified', 'concreteRegDetailed')

UNION ALL

-- 2b. Concrete Registers — mitigation rows
SELECT
    'Concrete Register'::text                                                     AS data_source,
    'mitigation'::text                                                            AS row_type,
    'Concrete'::text                                                              AS sub_category,
    COALESCE(extra_fields->>'component_type', '(unspecified)')                    AS item,
    0::numeric                                                                    AS actual_tco2e,
    COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)      AS mitigation_tco2e,
    COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)      AS base_case_tco2e,
    extra_fields->>'unit_code'                                                    AS unit
FROM activity_data
WHERE
    project_id                    = :project_id
    AND project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
    AND ui_table_key IN ('concreteRegSimplified-mitigation', 'concreteRegDetailed-mitigation')

UNION ALL

-- 3. Shortcut — IS Materials (non-maintenance rows)
SELECT
    'IS Materials (Shortcut)'::text                                               AS data_source,
    'actual'::text                                                                AS row_type,
    'Other shortcuts'::text                                                       AS sub_category,
    COALESCE(
        NULLIF(extra_fields->>'component_type', ''),
        NULLIF(extra_fields->>'sub_component_type', ''),
        '(unspecified)'
    )                                                                             AS item,
    COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0)               AS actual_tco2e,
    GREATEST(0,
        COALESCE(NULLIF(extra_fields->>'base_case',   '')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0)
    )                                                                             AS mitigation_tco2e,
    COALESCE(NULLIF(NULLIF(extra_fields->>'base_case', ''), '-')::numeric, 0)                 AS base_case_tco2e,
    NULL::text                                                                    AS unit
FROM activity_data
WHERE
    project_id                    = :project_id
    AND project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
    AND ui_table_key = 'shortcutIsMaterials'
    AND (extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')

UNION ALL

-- 4. Shortcut — SAT4P (A1-A4 sources only)
SELECT
    'SAT4P (Shortcut)'::text                                                      AS data_source,
    'actual'::text                                                                AS row_type,
    'Other shortcuts'::text                                                       AS sub_category,
    extra_fields->>'source'                                                       AS item,
    COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)         AS actual_tco2e,
    GREATEST(0,
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
            COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0) -
        COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) -
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
    )                                                                             AS mitigation_tco2e,
    COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
        COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0)           AS base_case_tco2e,
    NULL::text                                                                    AS unit
FROM activity_data
WHERE
    project_id                    = :project_id
    AND project_stage_instance_id = :stage_instance_id
    AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
    AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
    AND ui_table_key = 'shortcutSat4p'
    AND extra_fields->>'source' IN (
        'Construction materials',
        'Transport (construction materials)'
    )

ORDER BY sub_category, data_source, item
""")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bind(
    project_id: UUID,
    stage_instance_id: UUID,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    return {
        "project_id": str(project_id),
        "stage_instance_id": str(stage_instance_id),
        "project_option_id": str(project_option_id) if project_option_id else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=HotspotsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Materials hotspots summary — A1-A4 emissions by sub-category",
    description=(
        "Returns materials emissions aggregated by sub-category for the "
        "'Materials Hotspots' dashboard screen.\n\n"
        "- **rows** — per sub-category figures sorted by `base_case_tco2e` descending; "
        "drives both the left table (*Emissions from materials*) and the "
        "stacked bar chart (*Materials emissions by type*)\n"
        "- **total_\\*** — grand totals across all sub-categories\n\n"
        "Data sources included: Grade 3/4 detailed level (bcDetailedLevel, replDetailed, "
        "opEnergyDetailed), concrete registers (concreteRegSimplified, concreteRegDetailed), "
        "IS Materials shortcut (shortcutIsMaterials), SAT4P shortcut (shortcutSat4p).\n\n"
        "Mitigation rows are identified by the `{tableKey}-mitigation` ui_table_key convention."
    ),
)
async def get_hotspots_summary(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> HotspotsSummaryResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        result = await db.execute(_SUMMARY_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = [
        HotspotSummaryRow(
            sub_category=row.sub_category,
            actual_tco2e=row.actual_tco2e or Decimal("0"),
            mitigation_tco2e=row.mitigation_tco2e or Decimal("0"),
            base_case_tco2e=row.base_case_tco2e or Decimal("0"),
        )
        for row in result.mappings().all()
    ]

    total_actual = sum(r.actual_tco2e for r in rows)
    total_mit    = sum(r.mitigation_tco2e for r in rows)
    total_base   = sum(r.base_case_tco2e for r in rows)

    return HotspotsSummaryResponse(
        rows=rows,
        total_actual_tco2e=total_actual,
        total_mitigation_tco2e=total_mit,
        total_base_case_tco2e=total_base,
    )


@router.get(
    "/detail",
    response_model=HotspotsDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Materials hotspots detail — all contributing rows (for 'View detailed results')",
    description=(
        "Returns every individual row that contributes to the materials hotspots totals.\n\n"
        "Intended for the separate 'View detailed results' page.\n\n"
        "Columns: Data Source | Row Type | Sub-category | Item | "
        "Actual (tCO₂e) | Mitigation (tCO₂e) | Base Case (tCO₂e) | Unit\n\n"
        "**row_type** values:\n"
        "- `actual` — the base activity row\n"
        "- `mitigation` — a `{tableKey}-mitigation` row (Grade 3/4 and concrete registers only)"
    ),
)
async def get_hotspots_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> HotspotsDetailResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        result = await db.execute(_DETAIL_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = [
        HotspotDetailRow(
            data_source=row.data_source,
            row_type=row.row_type,
            sub_category=row.sub_category,
            item=row.item,
            actual_tco2e=row.actual_tco2e or Decimal("0"),
            mitigation_tco2e=row.mitigation_tco2e or Decimal("0"),
            base_case_tco2e=row.base_case_tco2e or Decimal("0"),
            unit=row.unit,
        )
        for row in result.mappings().all()
    ]

    return HotspotsDetailResponse(rows=rows)
