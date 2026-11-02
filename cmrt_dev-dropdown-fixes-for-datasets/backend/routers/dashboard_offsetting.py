"""
routers/dashboard_offsetting.py

Dashboard Results API — Offsetting Summary

Returns two aggregated datasets for the "Offsetting summary" dashboard screen:
  1. offset_standards  — quantity grouped by offset standard (emissions_subcategory)
                         e.g. ACCU, VCU, VER, CER, Humanitarian, Industrial ...
  2. offset_categories — quantity grouped by offset project type (emissions_source)
                         e.g. Agricultural, CCS, Energy, Industrial, Transport ...

A second endpoint returns the full row-level detail for "View detailed results".

Data source: activity_data rows where:
  - project_id           = provided
  - project_stage_instance_id = provided
  - ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
  - extra_fields->>'emissions_category' = 'Offset'

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
from services.emissions_result_aggregates import emissions_totals_by_activity

router = APIRouter(
    prefix="/api/dashboard/offsetting",
    tags=["Dashboard - Offsetting Summary"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OffsetAggRow(DashboardBase):
    """One bar in the chart — a name/label and its summed quantity."""
    name: str
    quantity: Decimal


class OffsetSummaryResponse(DashboardBase):
    """
    Two grouped datasets for the Offsetting Summary dashboard charts.

    offset_standards  → "Offset standards purchased" chart
    offset_categories → "Offset categories purchased" chart
    """
    offset_standards: List[OffsetAggRow]
    offset_categories: List[OffsetAggRow]


# Grade 3/4 detailed-level table keys that contain offsetting rows
_OFFSET_TABLE_KEYS = ("bcDetailedLevel", "constructionG3", "recurringG3")


class OffsetDetailRow(DashboardBase):
    """One row as entered by the user — for the 'View detailed results' table.

    Columns: Emissions Category | Emissions Sub-Category | Emissions Source |
             Unit | Quantity (Unit) | Emissions (tCO2e) | Notes
    """
    id: UUID
    emissions_category: Optional[str]     # extra_fields->>'emissions_category'
    emissions_subcategory: Optional[str]  # extra_fields->>'emissions_subcategory'
    emissions_source: Optional[str]       # extra_fields->>'emissions_source'
    unit: Optional[str]                   # extra_fields->>'unit_code'
    quantity: Decimal                     # Quantity (Unit)
    emissions_tco2e: Optional[Decimal]    # extra_fields->>'total_emissions_tco2e'
    notes: Optional[str]


class OffsetDetailResponse(DashboardBase):
    rows: List[OffsetDetailRow]


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

_STANDARDS_SQL = text("""
    SELECT
        COALESCE(extra_fields->>'emissions_subcategory', '(unspecified)') AS name,
        SUM(quantity)                                                      AS quantity
    FROM activity_data
    WHERE
        project_id                = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Offset'
        AND quantity > 0
    GROUP BY extra_fields->>'emissions_subcategory'
    ORDER BY quantity DESC
""")

_CATEGORIES_SQL = text("""
    SELECT
        COALESCE(extra_fields->>'emissions_source', '(unspecified)') AS name,
        SUM(quantity)                                                 AS quantity
    FROM activity_data
    WHERE
        project_id                = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Offset'
        AND quantity > 0
    GROUP BY extra_fields->>'emissions_source'
    ORDER BY quantity DESC
""")

_DETAIL_SQL = text("""
    SELECT
        id,
        extra_fields->>'emissions_category'                               AS emissions_category,
        extra_fields->>'emissions_subcategory'                            AS emissions_subcategory,
        extra_fields->>'emissions_source'                                 AS emissions_source,
        extra_fields->>'unit_code'                                          AS unit,
        quantity,
        0::numeric AS emissions_tco2e,
        extra_fields->>'notes'                                            AS notes
    FROM activity_data
    WHERE
        project_id                = :project_id
        AND project_stage_instance_id = :stage_instance_id
        AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
        AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
        AND ui_table_key IN ('bcDetailedLevel', 'constructionG3', 'recurringG3')
        AND extra_fields->>'emissions_category' = 'Offset'
    ORDER BY created_at
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
    response_model=OffsetSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Offsetting summary — two chart datasets",
    description=(
        "Returns aggregated offsetting data for the dashboard:\n\n"
        "- **offset_standards** — total quantity grouped by offset standard "
        "(e.g. ACCU, VCU, VER, CER, Humanitarian, Industrial)\n"
        "- **offset_categories** — total quantity grouped by offset project type "
        "(e.g. Agricultural, CCS, Energy efficiency, Transport)"
    ),
)
async def get_offsetting_summary(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> OffsetSummaryResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        standards_result = await db.execute(_STANDARDS_SQL, params)
        categories_result = await db.execute(_CATEGORIES_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    standards = [
        OffsetAggRow(name=row.name, quantity=row.quantity)
        for row in standards_result.mappings().all()
    ]
    categories = [
        OffsetAggRow(name=row.name, quantity=row.quantity)
        for row in categories_result.mappings().all()
    ]

    return OffsetSummaryResponse(
        offset_standards=standards,
        offset_categories=categories,
    )


@router.get(
    "/detail",
    response_model=OffsetDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Offsetting detail — all rows (for 'View detailed results')",
    description=(
        "Returns every individual offsetting entry for the given project/stage/option.\n\n"
        "Intended for the 'View detailed results' table that opens from the dashboard."
    ),
)
async def get_offsetting_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> OffsetDetailResponse:
    params = _bind(project_id, stage_instance_id, project_option_id, submission_period_id)

    try:
        result = await db.execute(_DETAIL_SQL, params)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        )

    raw_rows = result.mappings().all()
    emissions_by_id = await emissions_totals_by_activity(
        db, (row.id for row in raw_rows), measures=("offset",)
    )
    rows = [
        OffsetDetailRow(
            id=row.id,
            emissions_category=row.emissions_category,
            emissions_subcategory=row.emissions_subcategory,
            emissions_source=row.emissions_source,
            unit=row.unit,
            quantity=row.quantity,
            emissions_tco2e=emissions_by_id.get(row.id, Decimal(0)),
            notes=row.notes,
        )
        for row in raw_rows
    ]

    return OffsetDetailResponse(rows=rows)
