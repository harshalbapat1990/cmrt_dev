"""
routers/dashboard_waste.py

Dashboard Results API — Waste & Recycle Materials

Returns aggregated waste datasets for the "Waste & recycle materials" dashboard screen:
  1. waste_by_type      — mass (t) grouped by waste type (emissions_source)
                          e.g. Inert waste - Metals, Food, Spoil, Paper and cardboard ...
  2. waste_by_treatment — mass (t) grouped by waste treatment type (emissions_subcategory)
                          e.g. Waste to recycling, Waste to landfill,
                               Waste reuse (onsite), Waste reuse (offsite)
  3. waste_table        — individual rows for the "Detailed tables: Waste" inline table
                          columns: Waste Treatment | Waste Type | Quantity (t)
  4. totals             — total_waste_t, total_spoil_t, total_waste_excl_spoil_t

A second endpoint returns the full row-level detail for the "View detailed results" page.

Data source: activity_data rows where:
  - project_id                = provided
  - project_stage_instance_id = provided
  - ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  - extra_fields->>'emissions_category' = 'Waste'

Field mapping (extra_fields JSONB):
  emissions_subcategory → waste treatment type
  emissions_source      → waste type
  unit_code             → unit (t)
  total_emissions_tco2e → calculated emissions tCO2e

Query params
------------
  project_id          UUID  required
  stage_instance_id   UUID  required
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
    prefix="/api/dashboard/waste",
    tags=["Dashboard - Waste & Recycle Materials"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class WasteAggRow(DashboardBase):
    """One row in a grouped chart/table — a name/label and its summed mass (t)."""
    name: str
    quantity_t: Decimal


class WasteTableRow(DashboardBase):
    """One row for the inline 'Detailed tables: Waste' shown on the dashboard.

    Columns: Waste Treatment | Waste Type | Quantity (t)
    """
    waste_treatment: Optional[str]  # extra_fields->>'emissions_subcategory'
    waste_type: Optional[str]       # extra_fields->>'emissions_source'
    quantity_t: Decimal             # quantity (t)


class WasteTotals(DashboardBase):
    """Summary totals shown at the bottom of the Waste dashboard."""
    total_waste_t: Decimal
    total_spoil_t: Decimal
    total_waste_excl_spoil_t: Decimal


class WasteSummaryResponse(DashboardBase):
    """
    Aggregated datasets for the Waste & Recycle Materials dashboard.

    waste_by_type      → "Waste breakdown" table/chart (by waste type)
    waste_by_treatment → "Waste treatment type" table/chart
    waste_table        → "Detailed tables: Waste" inline table (treatment + type + qty)
    totals             → summary figures at bottom of dashboard
    """
    waste_by_type: List[WasteAggRow]
    waste_by_treatment: List[WasteAggRow]
    waste_table: List[WasteTableRow]
    totals: WasteTotals


class WasteDetailRow(DashboardBase):
    """One row for the 'View detailed results' separate page.

    Columns: Waste Treatment | Waste Type | Unit | Quantity (t) | Emissions (tCO2e) | Notes
    """
    id: UUID
    waste_treatment: Optional[str]     # extra_fields->>'emissions_subcategory'
    waste_type: Optional[str]          # extra_fields->>'emissions_source'
    unit: Optional[str]                # extra_fields->>'unit_code'
    quantity_t: Decimal                # quantity (t)
    emissions_tco2e: Optional[Decimal] # extra_fields->>'total_emissions_tco2e'
    notes: Optional[str]


class WasteDetailResponse(DashboardBase):
    rows: List[WasteDetailRow]


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

# Grade 3/4 detailed-level table keys that carry Waste rows
_WASTE_TABLE_KEYS = ("bcDetailedLevel", "constructionG3", "recurringG3")

_BY_TYPE_SQL = text("""
    SELECT
        COALESCE(extra_fields->>'emissions_source', '(unspecified)') AS name,
        SUM(quantity)                                                AS quantity_t
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Waste'
        AND quantity > 0
    GROUP BY extra_fields->>'emissions_source'
    ORDER BY quantity_t DESC
""")

_BY_TREATMENT_SQL = text("""
    SELECT
        COALESCE(extra_fields->>'emissions_subcategory', '(unspecified)') AS name,
        SUM(quantity)                                                      AS quantity_t
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Waste'
        AND quantity > 0
    GROUP BY extra_fields->>'emissions_subcategory'
    ORDER BY quantity_t DESC
""")

_TOTALS_SQL = text("""
    SELECT
        COALESCE(SUM(quantity), 0)                                          AS total_waste_t,
        COALESCE(SUM(quantity) FILTER (
            WHERE extra_fields->>'emissions_source' = 'Spoil'
        ), 0)                                                               AS total_spoil_t
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Waste'
        AND quantity > 0
""")

_WASTE_TABLE_SQL = text("""
    SELECT
        extra_fields->>'emissions_subcategory'  AS waste_treatment,
        extra_fields->>'emissions_source'       AS waste_type,
        quantity                                AS quantity_t
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Waste'
        AND quantity > 0
    ORDER BY extra_fields->>'emissions_subcategory', extra_fields->>'emissions_source'
""")

_DETAIL_SQL = text("""
    SELECT
        id,
        extra_fields->>'emissions_subcategory'                        AS waste_treatment,
        extra_fields->>'emissions_source'                             AS waste_type,
        extra_fields->>'unit_code'                                    AS unit,
        quantity                                                      AS quantity_t,
        NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric   AS emissions_tco2e,
        extra_fields->>'notes'                                        AS notes
    FROM activity_data
    WHERE
        project_id                    = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Waste'
    ORDER BY extra_fields->>'emissions_subcategory', extra_fields->>'emissions_source', created_at
""")


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=WasteSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Waste summary — breakdown by type, treatment type, inline table, and totals",
    description=(
        "Returns aggregated waste data for the dashboard:\n\n"
        "- **waste_by_type** — mass (t) grouped by waste type "
        "(e.g. Inert waste - Metals, Food, Spoil)\n"
        "- **waste_by_treatment** — mass (t) grouped by treatment type "
        "(e.g. Waste to recycling, Waste to landfill, Waste reuse onsite/offsite)\n"
        "- **waste_table** — individual rows for the \"Detailed tables: Waste\" inline table "
        "(Waste Treatment | Waste Type | Quantity (t))\n"
        "- **totals** — total waste (t), total spoil (t), total waste excl. spoil (t)"
    ),
)
async def get_waste_summary(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> WasteSummaryResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        by_type_result = await db.execute(_BY_TYPE_SQL, params)
        by_treatment_result = await db.execute(_BY_TREATMENT_SQL, params)
        waste_table_result = await db.execute(_WASTE_TABLE_SQL, params)
        totals_result = await db.execute(_TOTALS_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    waste_by_type = [
        WasteAggRow(name=row.name, quantity_t=row.quantity_t)
        for row in by_type_result.mappings().all()
    ]
    waste_by_treatment = [
        WasteAggRow(name=row.name, quantity_t=row.quantity_t)
        for row in by_treatment_result.mappings().all()
    ]
    waste_table = [
        WasteTableRow(
            waste_treatment=row.waste_treatment,
            waste_type=row.waste_type,
            quantity_t=row.quantity_t,
        )
        for row in waste_table_result.mappings().all()
    ]

    totals_row = totals_result.mappings().one()
    total_waste = totals_row.total_waste_t
    total_spoil = totals_row.total_spoil_t
    totals = WasteTotals(
        total_waste_t=total_waste,
        total_spoil_t=total_spoil,
        total_waste_excl_spoil_t=total_waste - total_spoil,
    )

    return WasteSummaryResponse(
        waste_by_type=waste_by_type,
        waste_by_treatment=waste_by_treatment,
        waste_table=waste_table,
        totals=totals,
    )


@router.get(
    "/detail",
    response_model=WasteDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Waste detail — all rows (for 'View detailed results' page)",
    description=(
        "Returns every individual waste entry for the given project/stage/option.\n\n"
        "Intended for the separate 'View detailed results' page.\n\n"
        "Columns: Waste Treatment | Waste Type | Unit | Quantity (t) | Emissions (tCO2e) | Notes"
    ),
)
async def get_waste_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> WasteDetailResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        result = await db.execute(_DETAIL_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    rows = [
        WasteDetailRow(
            id=row.id,
            waste_treatment=row.waste_treatment,
            waste_type=row.waste_type,
            unit=row.unit,
            quantity_t=row.quantity_t,
            emissions_tco2e=row.emissions_tco2e,
            notes=row.notes,
        )
        for row in result.mappings().all()
    ]

    return WasteDetailResponse(rows=rows)
