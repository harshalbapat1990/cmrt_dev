"""
routers/org_dashboard_waste.py

Organisational Dashboard — Waste & Recycle Materials

Aggregates waste data across all projects belonging to the given organisation,
with optional filters by project class, program name, and submission stage.

Two endpoints:
  GET /api/org-dashboard/waste/summary  — breakdown by type, treatment, table, and totals
  GET /api/org-dashboard/waste/detail   — row-level breakdown (includes project info)
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
from services.emissions_result_aggregates import emissions_totals_by_activity

router = APIRouter(
    prefix="/api/org-dashboard/waste",
    tags=["Org Dashboard - Waste"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class WasteNameQuantityRow(DashboardBase):
    name: str
    quantity_t: Decimal


class WasteTableRow(DashboardBase):
    waste_treatment: Optional[str]
    waste_type: Optional[str]
    quantity_t: Optional[Decimal]


class WasteTotals(DashboardBase):
    total_waste_t: Decimal
    total_spoil_t: Decimal
    total_waste_excl_spoil_t: Decimal


class WasteSummaryResponse(DashboardBase):
    waste_by_type: List[WasteNameQuantityRow]
    waste_by_treatment: List[WasteNameQuantityRow]
    waste_table: List[WasteTableRow]
    totals: WasteTotals


class WasteDetailRow(DashboardBase):
    id: UUID
    project_id: UUID
    project_name: str
    waste_treatment: Optional[str]
    waste_type: Optional[str]
    unit: Optional[str]
    quantity_t: Optional[Decimal]
    emissions_tco2e: Optional[Decimal]
    notes: Optional[str]


class WasteDetailResponse(DashboardBase):
    rows: List[WasteDetailRow]


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

_BY_TYPE_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id               AS project_id,
        p.project_name     AS project_name,
        psi.id             AS stage_instance_id
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
SELECT
    COALESCE(ad.extra_fields->>'emissions_source', '(unspecified)') AS name,
    SUM(ad.quantity)                                                AS quantity_t
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND ad.extra_fields->>'emissions_category' = 'Waste'
  AND ad.quantity > 0
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
GROUP BY ad.extra_fields->>'emissions_source'
ORDER BY quantity_t DESC
""")

_BY_TREATMENT_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id               AS project_id,
        p.project_name     AS project_name,
        psi.id             AS stage_instance_id
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
SELECT
    COALESCE(ad.extra_fields->>'emissions_subcategory', '(unspecified)') AS name,
    SUM(ad.quantity)                                                     AS quantity_t
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND ad.extra_fields->>'emissions_category' = 'Waste'
  AND ad.quantity > 0
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
GROUP BY ad.extra_fields->>'emissions_subcategory'
ORDER BY quantity_t DESC
""")

_TOTALS_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id               AS project_id,
        p.project_name     AS project_name,
        psi.id             AS stage_instance_id
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
SELECT
    COALESCE(SUM(ad.quantity), 0)                                             AS total_waste_t,
    COALESCE(SUM(ad.quantity) FILTER (
        WHERE ad.extra_fields->>'emissions_source' = 'Spoil'
    ), 0)                                                                     AS total_spoil_t
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND ad.extra_fields->>'emissions_category' = 'Waste'
  AND ad.quantity > 0
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
""")

_WASTE_TABLE_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id               AS project_id,
        p.project_name     AS project_name,
        psi.id             AS stage_instance_id
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
SELECT
    ad.extra_fields->>'emissions_subcategory' AS waste_treatment,
    ad.extra_fields->>'emissions_source'      AS waste_type,
    ad.quantity                               AS quantity_t
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND ad.extra_fields->>'emissions_category' = 'Waste'
  AND ad.quantity > 0
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
ORDER BY ad.extra_fields->>'emissions_subcategory', ad.extra_fields->>'emissions_source'
""")

_DETAIL_SQL = text("""
WITH eligible_projects AS (
    SELECT DISTINCT
        p.id               AS project_id,
        p.project_name     AS project_name,
        psi.id             AS stage_instance_id
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
SELECT
    ad.id                                                                          AS id,
    ep.project_id                                                                  AS project_id,
    ep.project_name                                                                AS project_name,
    ad.extra_fields->>'emissions_subcategory'                                      AS waste_treatment,
    ad.extra_fields->>'emissions_source'                                           AS waste_type,
    ad.extra_fields->>'unit_code'                                                  AS unit,
    ad.quantity                                                                    AS quantity_t,
    0::numeric AS emissions_tco2e,
    ad.extra_fields->>'notes'                                                      AS notes
FROM activity_data ad
JOIN eligible_projects ep
    ON ep.project_id        = ad.project_id
   AND ep.stage_instance_id = ad.project_stage_instance_id
WHERE ad.ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  AND ad.extra_fields->>'emissions_category' = 'Waste'
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
ORDER BY ep.project_name, ad.extra_fields->>'emissions_subcategory', ad.extra_fields->>'emissions_source', ad.created_at
""")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=WasteSummaryResponse)
async def org_waste_summary(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns waste aggregated by type, treatment, table rows, and totals across all org projects."""
    params = _bind(
        org_id,
        project_class=_normalize_project_class(project_class),
        program_name=program_name,
        stage=_normalize_stage(stage),
        project_type_id=project_type_id,
        project_typecast_id=project_typecast,
    )
    try:
        by_type_res      = await db.execute(_BY_TYPE_SQL,      params)
        by_treatment_res = await db.execute(_BY_TREATMENT_SQL, params)
        totals_res       = await db.execute(_TOTALS_SQL,       params)
        table_res        = await db.execute(_WASTE_TABLE_SQL,  params)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Database query failed: {exc}") from exc

    by_type_rows      = [WasteNameQuantityRow(**dict(r)) for r in by_type_res.mappings().all()]
    by_treatment_rows = [WasteNameQuantityRow(**dict(r)) for r in by_treatment_res.mappings().all()]
    waste_table_rows  = [WasteTableRow(**dict(r)) for r in table_res.mappings().all()]

    totals_row = totals_res.mappings().first()
    total_waste = Decimal(str(totals_row["total_waste_t"])) if totals_row else Decimal(0)
    total_spoil = Decimal(str(totals_row["total_spoil_t"])) if totals_row else Decimal(0)

    totals = WasteTotals(
        total_waste_t=total_waste,
        total_spoil_t=total_spoil,
        total_waste_excl_spoil_t=total_waste - total_spoil,
    )

    return WasteSummaryResponse(
        waste_by_type=by_type_rows,
        waste_by_treatment=by_treatment_rows,
        waste_table=waste_table_rows,
        totals=totals,
    )


@router.get("/detail", response_model=WasteDetailResponse)
async def org_waste_detail(
    org_id: UUID = Query(..., description="Organisation UUID"),
    project_class: Optional[str] = Query(None),
    program_name: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    project_type_id: Optional[UUID] = Query(None, description="Filter by project type (benchmark mastertype UUID)"),
    project_typecast: Optional[UUID] = Query(None, description="Filter by project typecast UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Returns every individual waste entry across all projects in the organisation."""
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

    emissions_by_id = await emissions_totals_by_activity(db, (r["id"] for r in rows))
    return WasteDetailResponse(rows=[
        WasteDetailRow(**{**dict(r), "emissions_tco2e": emissions_by_id.get(r["id"], Decimal(0))})
        for r in rows
    ])
