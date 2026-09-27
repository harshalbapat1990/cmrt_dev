"""
routers/dashboard_carbon_storage.py

Dashboard Results API — Carbon Storage (Detailed table)

Returns the row-level breakdown for the "Detailed tables: Carbon Storage" section.
Only Construction-stage data is in scope:
  • Component Level (Grade 2)  — ui_table_key = 'component'
  • Detailed Level  (Grade 3)  — ui_table_key = 'bcDetailedLevel'

Column derivations (matching the Excel table headers)
------------------------------------------------------
  input_table                               derived from ui_table_key
  category                                  extra_fields->>'emissions_category'
  sub_category                              extra_fields->>'emissions_subcategory'
  emissions_source                          extra_fields->>'emissions_source_name'
                                            (fallback: extra_fields->>'emissions_source')
  unit                                      extra_fields->>'unit_code'
  quantity                                  activity_data.quantity

  carbon_storage_ef  (tCO2e/UoM)           Looked up from:
    • Component Level → v_grade2_component_level
          JOIN ON Jurisdiction + Emissions Category
                + Emissions Sub-Category + Emissions Source
    • Detailed Level  → v_grade34_detailed_level
          JOIN ON Jurisdiction + Emissions Source + UoM

  carbon_storage_tco2e (tCO2e)             = quantity × carbon_storage_ef

Note on data availability
--------------------------
  The "Carbon Storage (tCO2e/UoM)" column exists in both lookup views as a pivot
  column but values may currently be NULL (not yet seeded in background_grade_metrics).
  All calculations use COALESCE(..., 0) so the endpoint is fully functional now and
  will auto-populate correct values once the underlying metric data is seeded.
  The Offset category is excluded per spec.

Endpoint
--------
  GET /api/dashboard/carbon-storage/detail

Query params
------------
  project_id          UUID   required
  stage_instance_id   UUID   required
  project_option_id   UUID   optional
  submission_period_id UUID  optional
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from services.project_context_helper import ProjectContextHelper
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from models.emissions_results import EmissionsResult
from sqlalchemy import select

router = APIRouter(
    prefix="/api/dashboard/carbon-storage",
    tags=["Dashboard - Carbon Storage"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CarbonStorageDetailRow(DashboardBase):
    """
    One row for the 'Detailed tables: Carbon Storage' grid.

    Columns map 1-to-1 to the Excel table headers.
    carbon_storage_ef will be None until the lookup-view metric data is seeded.
    carbon_storage_tco2e will be 0 until seeded.
    """
    id: UUID
    input_table: str                         # "Component Level" | "Detailed Level"
    category: Optional[str]                  # Emissions Category
    sub_category: Optional[str]              # Emissions Sub-Category
    emissions_source: Optional[str]          # Emissions Source
    unit: Optional[str]                      # Unit of Measure
    quantity: Optional[Decimal]              # Quantity
    carbon_storage_ef: Optional[Decimal]     # Carbon Storage Emission Factor (tCO2e/UoM)
    carbon_storage_tco2e: Decimal            # Carbon Storage (tCO2e) = quantity × EF


class CarbonStorageDetailResponse(DashboardBase):
    rows: List[CarbonStorageDetailRow]
    total_carbon_storage_tco2e: Decimal      # Sum of all carbon_storage_tco2e values


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_DETAIL_SQL = text("""
-- ── 1. Grade 2 Component Level ──────────────────────────────────────────────
-- Joins v_grade2_component_level on Jurisdiction + Category + Sub-Category + Source
-- to retrieve the "Carbon Storage (tCO2e/UoM)" emission factor.
SELECT
    ad.id,
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
LEFT JOIN v_grade2_component_level g2
    ON  g2."Jurisdiction"           = :jurisdiction
    AND g2."Emissions Category"     = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
    AND g2."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
    AND g2."Emissions Source"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
WHERE ad.project_id                    = CAST(:project_id        AS uuid)
  AND ad.project_stage_instance_id     = CAST(:stage_instance_id AS uuid)
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'component'
  AND COALESCE(ad.extra_fields->>'emissions_category', '') <> 'Offset'

UNION ALL

-- ── 2. Grade 3/4 Detailed Level ─────────────────────────────────────────────
-- Joins v_grade34_detailed_level on Jurisdiction + Emissions Category
--   + Emissions Sub-Category + Emissions Source + UoM
-- to retrieve the "Carbon Storage (tCO2e/UoM)" emission factor.
-- Sub-Category is included to prevent fan-out when the same Source+UoM exists
-- under multiple sub-categories (e.g. "Wood" appears in both Waste to landfill
-- and Waste to recycling).
SELECT
    ad.id,
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
LEFT JOIN v_grade34_detailed_level g34
    ON  g34."Jurisdiction"             = :jurisdiction
    AND g34."Emissions Category"       = COALESCE(NULLIF(ad.extra_fields->>'emissions_category',    ''), '__no_match__')
    AND g34."Emissions Sub-Category"   = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
    AND g34."Emissions Source"         = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
    AND g34."UoM"                      = COALESCE(NULLIF(ad.extra_fields->>'unit_code', ''), '__no_match__')
WHERE ad.project_id                    = CAST(:project_id        AS uuid)
  AND ad.project_stage_instance_id     = CAST(:stage_instance_id AS uuid)
  AND (CAST(:project_option_id    AS uuid) IS NULL OR ad.project_option_id    = CAST(:project_option_id    AS uuid))
  AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
  AND ad.ui_table_key = 'bcDetailedLevel'
  AND COALESCE(ad.extra_fields->>'emissions_category', '') <> 'Offset'

ORDER BY input_table, category, sub_category, emissions_source
""")


# ---------------------------------------------------------------------------
# Bind-params helper
# ---------------------------------------------------------------------------

def _bind(
    project_id: UUID,
    stage_instance_id: UUID,
    jurisdiction: str,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    return {
        "project_id":           str(project_id),
        "stage_instance_id":    str(stage_instance_id),
        "jurisdiction":         jurisdiction,
        "project_option_id":    str(project_option_id)    if project_option_id    else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/detail",
    response_model=CarbonStorageDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Carbon Storage detail — all rows (for 'Detailed tables: Carbon Storage' grid)",
    description=(
        "Returns every Construction-stage row that contributes to the Carbon Storage table.\n\n"
        "Sources:\n"
        "- **Component Level (Grade 2)** — `ui_table_key = 'component'`; "
        "emission factor looked up from `v_grade2_component_level`\n"
        "- **Detailed Level (Grade 3)** — `ui_table_key = 'bcDetailedLevel'`; "
        "emission factor looked up from `v_grade34_detailed_level`\n\n"
        "The `Offset` category is excluded. "
        "`carbon_storage_ef` will be `null` and `carbon_storage_tco2e` will be `0` "
        "for rows whose emission source has not yet been seeded in the lookup views."
    ),
)
async def get_carbon_storage_detail(
    project_id: UUID = Query(..., description="Project UUID"),
    stage_instance_id: UUID = Query(..., description="Stage instance UUID"),
    project_option_id: Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> CarbonStorageDetailResponse:
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
    params = _bind(project_id, stage_instance_id, jurisdiction, project_option_id, submission_period_id)

    try:
        result = await db.execute(_DETAIL_SQL, params)
        rows = result.mappings().all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {exc}",
        ) from exc

    result_query = select(EmissionsResult.activity_data_id, EmissionsResult.value).where(
        EmissionsResult.project_id == project_id,
        EmissionsResult.project_stage_instance_id == stage_instance_id,
        EmissionsResult.value_key == "stored_carbon",
    )
    result_values = {
        activity_id: Decimal(str(value or 0))
        for activity_id, value in (await db.execute(result_query)).all()
    }
    # The lookup view still supplies the displayed factor, while the reported
    # emissions amount comes from the canonical result ledger.
    detail_rows = []
    for raw in rows:
        values = dict(raw)
        values["carbon_storage_tco2e"] = result_values.get(values["id"], Decimal(0))
        detail_rows.append(CarbonStorageDetailRow(**values))
    total = sum((r.carbon_storage_tco2e for r in detail_rows), Decimal(0))

    return CarbonStorageDetailResponse(
        rows=detail_rows,
        total_carbon_storage_tco2e=total,
    )
