"""
routers/org_dashboard_carbon_storage.py

Organisational Dashboard — Carbon Storage

Aggregates carbon storage data across all projects belonging to the given
organisation, with optional filters by project class, program name, and
submission stage.

One endpoint:
  GET /api/org-dashboard/carbon-storage/detail  — row-level breakdown (includes project info)

Sources (Construction stage only):
  component       → Component Level (Grade 2)
  bcDetailedLevel → Detailed Level (Grade 3)

The jurisdiction for the EF lookup is resolved per-project from the
organisation's linked jurisdiction (proponent_org_id → organization → jurisdictions).
The 'Offset' category is excluded per spec.

Query params
------------
  org_id         UUID    required
  project_class  str     optional  (e.g. "SMALL", "LARGE")
  program_name   str     optional
  stage          str     optional  (e.g. "CONSTRUCTION", "RECURRING")
"""

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
    prefix="/api/org-dashboard/carbon-storage",
    tags=["Org Dashboard - Carbon Storage"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OrgCarbonStorageDetailRow(DashboardBase):
    """One row for the Org-level 'Detailed tables: Carbon Storage' grid."""
    id: UUID
    project_id: UUID
    project_name: str
    input_table: str                         # "Component Level" | "Detailed Level"
    category: Optional[str]                  # Emissions Category
    sub_category: Optional[str]              # Emissions Sub-Category
    emissions_source: Optional[str]          # Emissions Source
    unit: Optional[str]                      # Unit of Measure
    quantity: Optional[Decimal]              # Quantity
    carbon_storage_ef: Optional[Decimal]     # Carbon Storage EF (tCO2e/UoM)
    carbon_storage_tco2e: Decimal            # = quantity × EF


class OrgCarbonStorageDetailResponse(DashboardBase):
    rows: List[OrgCarbonStorageDetailRow]
    total_carbon_storage_tco2e: Decimal


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

_DETAIL_SQL = text("""
WITH eligible_projects AS (
    -- All (project, stage_instance) pairs for the organisation.
    -- Jurisdiction resolved per-project via proponent_org_id → organization → jurisdictions.
    SELECT DISTINCT
        p.id                            AS project_id,
        p.project_name                  AS project_name,
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
              WHERE po.project_id    = p.id
                AND po.organization_id = :org_id
          )
      )
      AND (CAST(:project_class AS TEXT) IS NULL OR p.project_class::text = CAST(:project_class AS TEXT))
      AND (CAST(:program_name  AS TEXT) IS NULL OR LOWER(p.program_name) = LOWER(CAST(:program_name AS TEXT)))
      AND (CAST(:stage         AS TEXT) IS NULL OR psi.stage::text        = CAST(:stage         AS TEXT))
      AND (CAST(:project_type_id AS uuid) IS NULL OR p.project_type_id = CAST(:project_type_id AS uuid))
    AND (CAST(:project_typecast_id AS uuid) IS NULL OR p.project_typecast_id = CAST(:project_typecast_id AS uuid))
)

-- ── 1. Grade 2 Component Level ──────────────────────────────────────────────
SELECT
    ad.id,
    ep.project_id,
    ep.project_name,
    'Component Level'::text                                               AS input_table,
    ad.extra_fields->>'emissions_category'                                AS category,
    ad.extra_fields->>'emissions_subcategory'                             AS sub_category,
    COALESCE(
        NULLIF(ad.extra_fields->>'emissions_source_name', ''),
        NULLIF(ad.extra_fields->>'emissions_source',      '')
    )                                                                     AS emissions_source,
    ad.extra_fields->>'unit_code'                                         AS unit,
    ad.quantity,
    g2."Carbon Storage (tCO2e/UoM)"                                       AS carbon_storage_ef,
    COALESCE(g2."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0)
                                                                          AS carbon_storage_tco2e
FROM activity_data ad
JOIN eligible_projects ep
    ON  ep.project_id        = ad.project_id
    AND ep.stage_instance_id = ad.project_stage_instance_id
LEFT JOIN v_grade2_component_level g2
    ON  g2."Jurisdiction"           = ep.jurisdiction
    AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
    AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
    AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
WHERE ad.ui_table_key = 'component'
  AND COALESCE(ad.extra_fields->>'emissions_category', '') <> 'Offset'
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

UNION ALL

-- ── 2. Grade 3/4 Detailed Level ─────────────────────────────────────────────
SELECT
    ad.id,
    ep.project_id,
    ep.project_name,
    'Detailed Level'::text                                                AS input_table,
    ad.extra_fields->>'emissions_category'                                AS category,
    ad.extra_fields->>'emissions_subcategory'                             AS sub_category,
    COALESCE(
        NULLIF(ad.extra_fields->>'emissions_source_name', ''),
        NULLIF(ad.extra_fields->>'emissions_source',      '')
    )                                                                     AS emissions_source,
    ad.extra_fields->>'unit_code'                                         AS unit,
    ad.quantity,
    g34."Carbon Storage (tCO2e/UoM)"                                      AS carbon_storage_ef,
    COALESCE(g34."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0)
                                                                          AS carbon_storage_tco2e
FROM activity_data ad
JOIN eligible_projects ep
    ON  ep.project_id        = ad.project_id
    AND ep.stage_instance_id = ad.project_stage_instance_id
LEFT JOIN v_grade34_detailed_level g34
    ON  g34."Jurisdiction"           = ep.jurisdiction
    AND g34."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
    AND g34."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
    AND g34."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    AND g34."UoM"                    = COALESCE(NULLIF(ad.extra_fields->>'unit_code',             ''), '__no_match__')
WHERE ad.ui_table_key = 'bcDetailedLevel'
  AND COALESCE(ad.extra_fields->>'emissions_category', '') <> 'Offset'
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))

ORDER BY project_name, input_table, category, sub_category, emissions_source
""")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/detail",
    response_model=OrgCarbonStorageDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Org Carbon Storage detail — all rows across all org projects",
    description=(
        "Returns every Construction-stage row contributing to Carbon Storage "
        "across all projects in the organisation.\n\n"
        "Sources:\n"
        "- **Component Level (Grade 2)** — `ui_table_key = 'component'`; "
        "EF from `v_grade2_component_level`\n"
        "- **Detailed Level (Grade 3)** — `ui_table_key = 'bcDetailedLevel'`; "
        "EF from `v_grade34_detailed_level`\n\n"
        "The jurisdiction for each project is resolved from the organisation profile. "
        "The `Offset` category is excluded."
    ),
)
async def org_carbon_storage_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None, description="Filter by project class (e.g. SMALL, LARGE)"),
    program_name: Optional[str] = Query(None, description="Filter by program name (case-insensitive)"),
    stage: Optional[str] = Query(None, description="Filter by stage type (e.g. CONSTRUCTION, RECURRING)"),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
) -> OrgCarbonStorageDetailResponse:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        ) from exc

    detail_rows = [OrgCarbonStorageDetailRow(**dict(r)) for r in rows]
    total = sum((r.carbon_storage_tco2e for r in detail_rows), Decimal(0))

    return OrgCarbonStorageDetailResponse(
        rows=detail_rows,
        total_carbon_storage_tco2e=total,
    )
