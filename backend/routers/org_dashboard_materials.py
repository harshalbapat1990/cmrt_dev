"""
routers/org_dashboard_materials.py

Organisational Dashboard — Materials use and composition

Aggregates materials data across all projects belonging to the given organisation,
with optional filters by project class, program name, and submission stage.

Two endpoints:
  GET /api/org-dashboard/materials/summary  — inline table and totals
  GET /api/org-dashboard/materials/detail   — row-level breakdown (includes project info)
"""

from decimal import Decimal
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from models.organizations import Organization

router = APIRouter(
    prefix="/api/org-dashboard/materials",
    tags=["Org Dashboard - Materials"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgMaterialsRow(DashboardBase):
    id: UUID
    project_id: UUID
    project_name: str
    input_table: str
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


class MaterialsTotals(DashboardBase):
    total_materials_t: Optional[Decimal]
    recycled_t: Optional[Decimal]
    reused_t: Optional[Decimal]
    virgin_t: Optional[Decimal]


class OrgMaterialsSummaryResponse(DashboardBase):
    materials_table: List[OrgMaterialsRow]
    totals: MaterialsTotals


class OrgMaterialsDetailResponse(DashboardBase):
    rows: List[OrgMaterialsRow]


# ---------------------------------------------------------------------------
# Jurisdiction helper
# ---------------------------------------------------------------------------

async def _fetch_org_jurisdiction(db: AsyncSession, org_id: UUID) -> str:
    """Return the jurisdiction name for the organisation. Falls back to 'Australia'."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if org and org.jurisdiction:
        return org.jurisdiction.name
    return "Australia"


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    org_id: UUID,
    project_class: Optional[str] = None,
    program_name: Optional[str] = None,
    stage: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    project_type_id: Optional[UUID] = None,
    project_typecast_id: Optional[UUID] = None,
) -> dict:
    return {
        "org_id": str(org_id),
        "project_class": project_class,
        "program_name": program_name,
        "stage": stage,
        "filter_by_jurisdiction": jurisdiction is not None,
        "jurisdiction": jurisdiction or "Global",
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

_MAIN_SQL = text("""
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
),

all_rows AS (

    -- 1. Grade 2 Component Level + Grade 3 Detailed Level (Materials only)
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        CASE ad.ui_table_key
            WHEN 'component' THEN 'Component Level'
            ELSE 'Detailed level'
        END                                                           AS input_table,
        COALESCE(
            NULLIF(ad.extra_fields->>'emissions_source_name', ''),
            NULLIF(ad.extra_fields->>'emissions_source',      '')
        )                                                             AS emissions_source,
        ad.extra_fields->>'emissions_subcategory'                     AS sub_category,
        ad.extra_fields->>'unit_code'                                 AS unit,
        ad.quantity                                                   AS quantity,
        ad.extra_fields->>'notes'                                     AS notes,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric AS emissions_tco2e,
        false                                                         AS is_concrete
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key IN ('component', 'bcDetailedLevel', 'constructionG3')
      AND ad.extra_fields->>'emissions_category' = 'Materials'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 2. Concrete Register – Simplified
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        'Concrete register - Simplified'                              AS input_table,
        'Concrete - ' || COALESCE(ad.extra_fields->>'strength', '')   AS emissions_source,
        CASE
            WHEN ad.extra_fields->>'mixType' = 'Precast' THEN 'Precast concrete'
            ELSE 'Concrete in-situ'
        END                                                           AS sub_category,
        'm3'                                                          AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'volume', ''), '-')::numeric  AS quantity,
        ad.extra_fields->>'notes'                                     AS notes,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric AS emissions_tco2e,
        true                                                          AS is_concrete
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'concreteRegSimplified'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

    UNION ALL

    -- 3. Concrete Register – Detailed
    SELECT
        ad.id,
        ep.project_id,
        ep.project_name,
        'Concrete register - Detailed'                                AS input_table,
        COALESCE(
            NULLIF(ad.extra_fields->>'mixId', ''),
            '(no mix ID)'
        )                                                             AS emissions_source,
        CASE
            WHEN ad.extra_fields->>'mixType' = 'Precast' THEN 'Precast concrete'
            ELSE 'Concrete in-situ'
        END                                                           AS sub_category,
        'm3'                                                          AS unit,
        NULLIF(NULLIF(ad.extra_fields->>'volume', ''), '-')::numeric  AS quantity,
        ad.extra_fields->>'notes'                                     AS notes,
        NULLIF(NULLIF(ad.extra_fields->>'total_emissions_tco2e', ''), '-')::numeric AS emissions_tco2e,
        true                                                          AS is_concrete
    FROM activity_data ad
    JOIN eligible_projects ep
        ON ep.project_id        = ad.project_id
       AND ep.stage_instance_id = ad.project_stage_instance_id
    WHERE ad.ui_table_key = 'concreteRegDetailed'
      AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

),

with_calcs AS (
    SELECT
        r.id,
        r.project_id,
        r.project_name,
        r.input_table,
        r.sub_category,
        r.emissions_source,
        r.unit,
        r.quantity,
        r.notes,
        r.emissions_tco2e,

        -- Density
        CASE WHEN r.unit = 't' THEN NULL ELSE dens.density END        AS density,

        -- Mass (tonnes)
        CASE
            WHEN r.unit = 't'             THEN r.quantity
            WHEN dens.density IS NOT NULL THEN r.quantity * dens.density
            ELSE NULL
        END                                                           AS mass_t,

        -- Recycled / Reused content fractions
        COALESCE(rcl.recycled_frac, 0)                                AS recycled_frac,
        COALESCE(rcl.reused_frac,   0)                                AS reused_frac

    FROM all_rows r

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
    project_id,
    project_name,
    input_table,
    sub_category,
    emissions_source,
    unit,
    quantity,
    density,
    mass_t,
    recycled_frac * 100                                               AS recycled_pct,
    CASE WHEN mass_t IS NOT NULL THEN mass_t * recycled_frac
         ELSE NULL END                                                AS recycled_t,
    reused_frac * 100                                                 AS reused_pct,
    CASE WHEN mass_t IS NOT NULL THEN mass_t * reused_frac
         ELSE NULL END                                                AS reused_t,
    CASE WHEN mass_t IS NOT NULL
         THEN mass_t * (1 - recycled_frac - reused_frac)
         ELSE NULL END                                                AS virgin_t,
    emissions_tco2e,
    notes
FROM with_calcs
ORDER BY project_name, input_table, sub_category, emissions_source
""")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=OrgMaterialsSummaryResponse)
async def org_materials_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns materials table rows and aggregate totals across all org projects."""
    jurisdiction = await _fetch_org_jurisdiction(db, org_id)
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        jurisdiction=jurisdiction,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_MAIN_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    materials_rows = [OrgMaterialsRow(**dict(r)) for r in rows]

    total_mass     = sum((r.mass_t     or Decimal(0) for r in materials_rows), Decimal(0))
    total_recycled = sum((r.recycled_t or Decimal(0) for r in materials_rows), Decimal(0))
    total_reused   = sum((r.reused_t   or Decimal(0) for r in materials_rows), Decimal(0))
    total_virgin   = sum((r.virgin_t   or Decimal(0) for r in materials_rows), Decimal(0))

    return OrgMaterialsSummaryResponse(
        materials_table=materials_rows,
        totals=MaterialsTotals(
            total_materials_t=total_mass,
            recycled_t=total_recycled,
            reused_t=total_reused,
            virgin_t=total_virgin,
        ),
    )


@router.get("/detail", response_model=OrgMaterialsDetailResponse)
async def org_materials_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns every individual materials row across all projects in the organisation."""
    jurisdiction = await _fetch_org_jurisdiction(db, org_id)
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        jurisdiction=jurisdiction,
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        result = await db.execute(_MAIN_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    return OrgMaterialsDetailResponse(rows=[OrgMaterialsRow(**dict(r)) for r in rows])
