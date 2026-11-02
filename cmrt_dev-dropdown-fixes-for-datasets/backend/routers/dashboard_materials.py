"""
routers/dashboard_materials.py

Dashboard Results API — Materials use and composition

Returns mass, recycled-content, reused-content and virgin-material figures drawn
from the four input tables that contribute to the "Materials use and composition"
dashboard screen:

  1. Component Level (Grade 2)         — ui_table_key = 'component',
                                          emissions_category = 'Materials'
  2. Detailed Level (Grade 3) materials — ui_table_key IN ('bcDetailedLevel',
                                          'constructionG3'),
                                          emissions_category = 'Materials'
  3. Concrete Register – Simplified    — ui_table_key = 'concreteRegSimplified'
  4. Concrete Register – Detailed      — ui_table_key = 'concreteRegDetailed'

Column derivations
------------------
  input_table       derived from ui_table_key
  sub_category      extra_fields->>'emissions_subcategory'; 'Concrete in-situ' or
                    'Precast concrete' for concrete tables (derived from mixType)
  emissions_source  extra_fields->>'emissions_source_name' for Grade 2/3 rows;
                    'Concrete - <strength>' for simplified concrete;
                    extra_fields->>'mixId' for detailed concrete
  unit              extra_fields->>'unit_code'; always 'm3' for concrete tables
  quantity          activity_data.quantity; extra_fields->>'volume' for concrete
  density           NULL when unit = 't'; non-concrete: looked up from
                    v_densities_detailed_level by Emissions Source; concrete:
                    looked up by Emissions Sub-Category = 'Concrete in-situ'
  mass_t            quantity when unit = 't'; quantity × density otherwise
  recycled_pct      looked up from recycled_content_factors (as %, i.e. 0–100);
                    0 if not found  (Excel: IFNA(XLOOKUP(source, Table2351038), 0))
  recycled_t        mass_t × recycled_pct/100
  reused_pct        looked up from recycled_content_factors; 0 if not found
  reused_t          mass_t × reused_pct/100
  virgin_t          mass_t − recycled_t − reused_t

Endpoints
---------
  GET /api/dashboard/materials/summary
      → materials_table  (List[MaterialsTableRow])  inline "Detailed tables" on dashboard
      → totals           (MaterialsTotals)

  GET /api/dashboard/materials/detail
      → rows             (List[MaterialsDetailRow])  "View detailed results" separate page

Query params
------------
  project_id          UUID   required
  stage_instance_id   UUID   required
  jurisdiction        str    optional  e.g. 'Australia' or 'New Zealand'
                             Used to prefer jurisdiction-specific densities and
                             recycled-content factors; falls back to 'Global' when omitted.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.project_context_helper import ProjectContextHelper
from services.emissions_result_aggregates import emissions_totals_by_activity

router = APIRouter(
    prefix="/api/dashboard/materials",
    tags=["Dashboard - Materials use and composition"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MaterialsTableRow(DashboardBase):
    """One row for the inline 'Detailed tables: Recycled materials' dashboard table."""
    input_table: Optional[str]
    sub_category: Optional[str]
    emissions_source: Optional[str]
    unit: Optional[str]
    quantity: Optional[Decimal]
    density: Optional[Decimal]       # t/UoM; NULL when unit already in tonnes
    mass_t: Optional[Decimal]
    recycled_pct: Optional[Decimal]  # 0–100 display value
    recycled_t: Optional[Decimal]
    reused_pct: Optional[Decimal]    # always 0 (not yet in DB)
    reused_t: Optional[Decimal]      # always 0
    virgin_t: Optional[Decimal]


class MaterialsTotals(DashboardBase):
    """Summary figures shown on the Materials use and composition dashboard."""
    total_materials_t: Decimal
    recycled_t: Decimal
    reused_t: Decimal
    virgin_t: Decimal


class MaterialsSummaryResponse(DashboardBase):
    """
    Aggregated materials data for the dashboard.

    materials_table → "Detailed tables: Recycled materials" inline table
    totals          → headline figures (total, recycled, reused, virgin)
    """
    materials_table: List[MaterialsTableRow]
    totals: MaterialsTotals


class MaterialsDetailRow(DashboardBase):
    """One row for the 'View detailed results' separate page."""
    id: UUID
    input_table: Optional[str]
    sub_category: Optional[str]
    emissions_source: Optional[str]
    unit: Optional[str]
    quantity: Optional[Decimal]
    density: Optional[Decimal]
    mass_t: Optional[Decimal]
    recycled_pct: Optional[Decimal]
    recycled_t: Optional[Decimal]
    reused_pct: Optional[Decimal]
    reused_t: Optional[Decimal]
    virgin_t: Optional[Decimal]
    emissions_tco2e: Optional[Decimal]
    notes: Optional[str]


class MaterialsDetailResponse(DashboardBase):
    rows: List[MaterialsDetailRow]


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_MATERIALS_SQL = text("""
WITH all_rows AS (

    -- ── 1. Grade 2 Component Level + Grade 3 Detailed Level (Materials only) ──
    SELECT
        ad.id,
        CASE ad.ui_table_key
            WHEN 'component' THEN 'Component Level'
            ELSE 'Detailed level'
        END                                                           AS input_table,
        COALESCE(
            NULLIF(extra_fields->>'emissions_source_name', ''),
            NULLIF(extra_fields->>'emissions_source',      '')
        )                                                             AS emissions_source,
        extra_fields->>'emissions_subcategory'                        AS sub_category,
        extra_fields->>'unit_code'                                    AS unit,
        ad.quantity                                                   AS quantity,
        extra_fields->>'notes'                                        AS notes,
        0::numeric AS emissions_tco2e,
        false                                                         AS is_concrete
    FROM activity_data ad
    WHERE
        ad.project_id                    = :project_id
        AND ad.project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        AND ad.ui_table_key IN ('component', 'bcDetailedLevel', 'constructionG3')
        AND extra_fields->>'emissions_category' = 'Materials'

    UNION ALL

    -- ── 2. Concrete Register – Simplified ────────────────────────────────────
    SELECT
        ad.id,
        'Concrete register - Simplified'                              AS input_table,
        'Concrete - ' || COALESCE(extra_fields->>'strength', '')      AS emissions_source,
        CASE
            WHEN extra_fields->>'mixType' = 'Precast' THEN 'Precast concrete'
            ELSE 'Concrete in-situ'
        END                                                           AS sub_category,
        'm3'                                                          AS unit,
        NULLIF(NULLIF(extra_fields->>'volume', ''), '-')::numeric                  AS quantity,
        extra_fields->>'notes'                                        AS notes,
        0::numeric AS emissions_tco2e,
        true                                                          AS is_concrete
    FROM activity_data ad
    WHERE
        ad.project_id                    = :project_id
        AND ad.project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        AND ad.ui_table_key = 'concreteRegSimplified'

    UNION ALL

    -- ── 3. Concrete Register – Detailed ──────────────────────────────────────
    SELECT
        ad.id,
        'Concrete register - Detailed'                                AS input_table,
        COALESCE(
            NULLIF(extra_fields->>'mixId', ''),
            '(no mix ID)'
        )                                                             AS emissions_source,
        CASE
            WHEN extra_fields->>'mixType' = 'Precast' THEN 'Precast concrete'
            ELSE 'Concrete in-situ'
        END                                                           AS sub_category,
        'm3'                                                          AS unit,
        NULLIF(NULLIF(extra_fields->>'volume', ''), '-')::numeric                  AS quantity,
        extra_fields->>'notes'                                        AS notes,
        0::numeric AS emissions_tco2e,
        true                                                          AS is_concrete
    FROM activity_data ad
    WHERE
        ad.project_id                    = :project_id
        AND ad.project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
        AND ad.ui_table_key = 'concreteRegDetailed'

),

with_calcs AS (
    SELECT
        r.id,
        r.input_table,
        r.sub_category,
        r.emissions_source,
        r.unit,
        r.quantity,
        r.notes,
        r.emissions_tco2e,

        -- ── Density ──────────────────────────────────────────────────────────
        -- NULL when unit is already tonnes (no conversion needed).
        -- Non-concrete rows: look up by 'Emissions Source' = emissions_source.
        -- Concrete rows:     look up by 'Emissions Sub-Category' = 'Concrete in-situ'
        --   (Excel: XLOOKUP("Concrete in-situ", tbl_densities[Emissions Sub-Category], ...))
        CASE WHEN r.unit = 't' THEN NULL ELSE dens.density END        AS density,

        -- ── Mass (tonnes) ─────────────────────────────────────────────────────
        CASE
            WHEN r.unit = 't'                 THEN r.quantity
            WHEN dens.density IS NOT NULL     THEN r.quantity * dens.density
            ELSE NULL
        END                                                           AS mass_t,

        -- ── Recycled / Reused content fractions (0–1, from recycled_content_factors) ─
        -- Applies to all row types; returns 0 if no match (IFNA fallback).
        -- Source: Excel Table2351038 / Recycled Content.csv.
        COALESCE(rcl.recycled_frac, 0)                                AS recycled_frac,
        COALESCE(rcl.reused_frac,   0)                                AS reused_frac

    FROM all_rows r

    -- Per-row density via LATERAL; skipped when unit = 't'.
    -- Bug fix: concrete rows must match on 'Emissions Sub-Category', not 'Emissions Source',
    -- because 'Concrete in-situ' is a Sub-Category value in v_densities_detailed_level.
    LEFT JOIN LATERAL (
        SELECT "Density" AS density
        FROM v_densities_detailed_level
        WHERE (
            (r.is_concrete = TRUE  AND "Emissions Sub-Category" = 'Concrete in-situ')
            OR
            (r.is_concrete = FALSE AND "Emissions Source"       = r.emissions_source)
        )
          AND (
              NOT :filter_by_jurisdiction
              OR "Jurisdiction" = :jurisdiction
              OR "Jurisdiction" = 'Global'
          )
        ORDER BY
            CASE
                WHEN :filter_by_jurisdiction AND "Jurisdiction" = :jurisdiction THEN 0
                WHEN "Jurisdiction" = 'Global' THEN 1
                ELSE 2
            END
        LIMIT 1
    ) dens ON (r.unit IS DISTINCT FROM 't')

    -- Per-row recycled/reused-content via LATERAL from recycled_content_factors.
    -- Applies to ALL rows (Excel formula has no concrete exclusion; IFNA returns 0
    -- when no match is found, which is what COALESCE achieves here).
    -- jurisdiction_id is resolved from the :jurisdiction name parameter via subquery.
    LEFT JOIN LATERAL (
        SELECT
            COALESCE(rcf.recycled_content_pct, 0) AS recycled_frac,
            COALESCE(rcf.reused_content_pct,   0) AS reused_frac
        FROM recycled_content_factors rcf
        WHERE rcf.emissions_source = r.emissions_source
          AND rcf.is_active = TRUE
          AND (
              NOT :filter_by_jurisdiction
              OR rcf.jurisdiction_id = (SELECT id FROM jurisdictions WHERE name = :jurisdiction LIMIT 1)
              OR rcf.jurisdiction_id IS NULL
          )
        ORDER BY
            CASE
                WHEN :filter_by_jurisdiction
                     AND rcf.jurisdiction_id = (SELECT id FROM jurisdictions WHERE name = :jurisdiction LIMIT 1) THEN 0
                ELSE 1
            END
        LIMIT 1
    ) rcl ON TRUE

    WHERE COALESCE(r.quantity, 0) > 0
)

SELECT
    id,
    input_table,
    sub_category,
    emissions_source,
    unit,
    quantity,
    density,
    mass_t,
    -- Display recycled % as 0–100  (Excel: mass_t * recycled_content_pct)
    recycled_frac * 100                                               AS recycled_pct,
    CASE WHEN mass_t IS NOT NULL THEN mass_t * recycled_frac
         ELSE NULL END                                                AS recycled_t,
    -- Display reused % as 0–100  (Excel: mass_t * reused_content_pct)
    reused_frac * 100                                                 AS reused_pct,
    CASE WHEN mass_t IS NOT NULL THEN mass_t * reused_frac
         ELSE NULL END                                                AS reused_t,
    -- Virgin = mass − recycled − reused  (Excel: mass_t - recycled_t - reused_t)
    CASE WHEN mass_t IS NOT NULL
         THEN mass_t * (1 - recycled_frac - reused_frac)
         ELSE NULL END                                                AS virgin_t,
    emissions_tco2e,
    notes
FROM with_calcs
ORDER BY input_table, sub_category, emissions_source
""")


def _bind(
    project_id: UUID,
    stage_instance_id: UUID,
    jurisdiction: Optional[str],
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    return {
        "project_id":               str(project_id),
        "stage_instance_id":        str(stage_instance_id),
        "filter_by_jurisdiction":   jurisdiction is not None,
        "jurisdiction":             jurisdiction or "Global",
        "project_option_id":        str(project_option_id) if project_option_id else None,
        "submission_period_id":     str(submission_period_id) if submission_period_id else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=MaterialsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Materials summary — inline table and totals",
    description=(
        "Returns materials use and composition data for the dashboard:\n\n"
        "- **materials_table** — individual rows for the \"Detailed tables: Recycled materials\" "
        "inline table (Input Table | Sub-Category | Emissions Source | Unit | Quantity | "
        "Density | Mass (t) | Recycled (%) | Recycled (t) | Reused (%) | Reused (t) | "
        "Virgin (t))\n"
        "- **totals** — total materials (t), recycled (t), reused (t), virgin materials (t)\n\n"
        "Density is looked up from `v_densities_detailed_level`; recycled content from "
        "`material_recycled_content`. Supply `jurisdiction` (e.g. `Australia`) to prefer "
        "jurisdiction-specific factors over Global defaults."
    ),
)
async def get_materials_summary(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> MaterialsSummaryResponse:
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
    params = _bind(project_id, stage_instance_id, jurisdiction, project_option_id, submission_period_id)

    try:
        result = await db.execute(_MATERIALS_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = result.mappings().all()

    materials_table = [
        MaterialsTableRow(
            input_table=row.input_table,
            sub_category=row.sub_category,
            emissions_source=row.emissions_source,
            unit=row.unit,
            quantity=row.quantity,
            density=row.density,
            mass_t=row.mass_t,
            recycled_pct=row.recycled_pct,
            recycled_t=row.recycled_t,
            reused_pct=row.reused_pct,
            reused_t=row.reused_t,
            virgin_t=row.virgin_t,
        )
        for row in rows
    ]

    # Compute totals in Python from the already-fetched rows
    _d = Decimal
    total_materials_t = sum(r.mass_t    or _d(0) for r in rows)
    recycled_t        = sum(r.recycled_t or _d(0) for r in rows)
    reused_t          = sum(r.reused_t   or _d(0) for r in rows)
    virgin_t          = sum(r.virgin_t   or _d(0) for r in rows)

    totals = MaterialsTotals(
        total_materials_t=total_materials_t,
        recycled_t=recycled_t,
        reused_t=reused_t,
        virgin_t=virgin_t,
    )

    return MaterialsSummaryResponse(
        materials_table=materials_table,
        totals=totals,
    )


@router.get(
    "/detail",
    response_model=MaterialsDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Materials detail — all rows (for 'View detailed results' page)",
    description=(
        "Returns every individual materials entry for the given project/stage.\n\n"
        "Intended for the separate 'View detailed results' page.\n\n"
        "Columns: Input Table | Sub-Category | Emissions Source | Unit | Quantity | "
        "Density | Mass (t) | Recycled (%) | Recycled (t) | Reused (%) | Reused (t) | "
        "Virgin (t) | Emissions (tCO2e) | Notes"
    ),
)
async def get_materials_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> MaterialsDetailResponse:
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
    params = _bind(project_id, stage_instance_id, jurisdiction, project_option_id, submission_period_id)

    try:
        result = await db.execute(_MATERIALS_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    raw_rows = result.mappings().all()
    emissions_by_id = await emissions_totals_by_activity(db, (row.id for row in raw_rows))
    rows = [
        MaterialsDetailRow(
            id=row.id,
            input_table=row.input_table,
            sub_category=row.sub_category,
            emissions_source=row.emissions_source,
            unit=row.unit,
            quantity=row.quantity,
            density=row.density,
            mass_t=row.mass_t,
            recycled_pct=row.recycled_pct,
            recycled_t=row.recycled_t,
            reused_pct=row.reused_pct,
            reused_t=row.reused_t,
            virgin_t=row.virgin_t,
            emissions_tco2e=emissions_by_id.get(row.id, Decimal(0)),
            notes=row.notes,
        )
        for row in raw_rows
    ]

    return MaterialsDetailResponse(rows=rows)
