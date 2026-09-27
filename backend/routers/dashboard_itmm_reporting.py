"""
routers/dashboard_itmm_reporting.py

Dashboard Results API — ITMM Reporting: LCA Module Breakdown

Returns a per-lifecycle-module comparison of Baseline vs Actual emissions,
with absolute and per-declared-unit columns, difference, and reduction
percentages.  Mirrors the structure of the ITMM Reporting table in the
Carbon Management & Reporting Tool.

─────────────────────────────────────────────────────────────────────────────
Table rows (in order)
─────────────────────────────────────────────────────────────────────────────
  a1_a3_excl_biogenic   — Product stage (A1-A3) - excl biogenic carbon
  a1_a3_biogenic        — Product stage (A1-A3) - sequestered biogenic carbon
  a4                    — Transport to site (A4)
  a5_construction       — Construction (A5)
  a5_land_use_change    — Land use change (A5)
  total_upfront         — Total upfront carbon (A1-A5) - excl biogenic carbon [subtotal]
  b1_1                  — Use - material emissions and removals (B1.1)
  b2_b5                 — Maintenance (B2), Repair (B3), Refurbishment and replacement (B4-B5)
  total_in_use_embodied — Total in-use embodied carbon (B1.1, B2-B5) [subtotal]
  b1_2                  — Use - operational processes (B1.2) [placeholder = 0]
  b6                    — Operational energy (B6)
  b7                    — Operational water (B7)
  total_in_use_operational — Total in-use operational carbon (B1.2, B6-B7) [subtotal]
  b8                    — Users (B8)

─────────────────────────────────────────────────────────────────────────────
Baseline vs Actual calculation
─────────────────────────────────────────────────────────────────────────────
  Actual  = identical to the Emissions Breakdown screen values per module
  Baseline = Actual + emissions from all Mitigations data-entry tables
             (avoidance + net substitution), allocated by module, PLUS
             the difference between Base Case and Actual Case for shortcut
             tables (shortcutIsMaterials, shortcutSat4p).

─────────────────────────────────────────────────────────────────────────────
Biogenic (stored carbon)
─────────────────────────────────────────────────────────────────────────────
  Both Baseline and Actual show the same stored_carbon value (mitigations
  do not change biogenic carbon amounts).

─────────────────────────────────────────────────────────────────────────────
A5 split
─────────────────────────────────────────────────────────────────────────────
  Construction A5 = total A5 emissions EXCLUDING bcDetailedLevel rows where
                    emissions_category = 'Vegetation'
  Land use change A5 = bcDetailedLevel rows where
                    emissions_category = 'Vegetation'

─────────────────────────────────────────────────────────────────────────────
Query params
─────────────────────────────────────────────────────────────────────────────
  project_id        UUID  required
  stage_instance_id UUID  required
  elec_method       str   optional — 'location' (default) | 'market'
  project_option_id UUID  optional — filter to a specific project option
  submission_period_id UUID optional — filter to a specific submission period
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
from services.emissions_result_aggregates import aggregate_emissions_results

router = APIRouter(
    prefix="/api/dashboard/itmm-reporting",
    tags=["Dashboard - ITMM Reporting"],
)

# Compatibility query used by the Ratings dashboard. It preserves the former
# one-row result contract while calculating actual/baseline module totals from
# the canonical result ledger.
_ITMM_SQL = text("""
    WITH facts AS (
        SELECT
            er.lifecycle_module_code AS module_code,
            er.source_category,
            er.reporting_measure,
            er.value
        FROM emissions_results er
        JOIN activity_data ad ON ad.id = er.activity_data_id
        WHERE er.project_id = CAST(:project_id AS uuid)
          AND er.project_stage_instance_id = CAST(:stage_instance_id AS uuid)
          AND ad.project_id = er.project_id
          AND ad.project_stage_instance_id = er.project_stage_instance_id
          AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
          AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
          AND er.is_supplementary IS FALSE
          AND (
              er.accounting_basis = 'common'
              OR (:elec_method = 'location' AND er.accounting_basis = 'location')
              OR (:elec_method = 'market' AND er.accounting_basis = 'market')
          )
    )
    SELECT
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A1-A3' AND reporting_measure = 'actual'), 0) AS actual_a1a3,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A4' AND reporting_measure = 'actual'), 0) AS actual_a4,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A5' AND source_category IS DISTINCT FROM 'Vegetation' AND reporting_measure = 'actual'), 0) AS actual_a5_construction,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A5' AND source_category = 'Vegetation' AND reporting_measure = 'actual'), 0) AS actual_a5_luc,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A5' AND source_category IS DISTINCT FROM 'Vegetation' AND reporting_measure IN ('actual', 'mitigation', 'baseline_adjustment')), 0) AS baseline_a5_construction,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'A5' AND source_category = 'Vegetation' AND reporting_measure IN ('actual', 'mitigation', 'baseline_adjustment')), 0) AS baseline_a5_luc,
        0::numeric AS actual_b1_2,
        0::numeric AS baseline_b1_2,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B2-5' AND reporting_measure = 'actual'), 0) AS actual_b2_b5,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B6' AND reporting_measure = 'actual'), 0) AS actual_b6,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B6' AND reporting_measure IN ('actual', 'mitigation', 'baseline_adjustment')), 0) AS baseline_b6,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B7' AND reporting_measure = 'actual'), 0) AS actual_b7,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B7' AND reporting_measure IN ('actual', 'mitigation', 'baseline_adjustment')), 0) AS baseline_b7,
        COALESCE(SUM(value) FILTER (WHERE module_code = 'B8' AND reporting_measure = 'actual'), 0) AS actual_b8
    FROM facts
""")


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ITMMModuleRow(DashboardBase):
    """One row in the ITMM Reporting LCA Module Breakdown table."""
    module_code: str
    module_label: str
    is_subtotal: bool = False
    baseline_absolute: Optional[Decimal] = None
    baseline_per_unit: Optional[Decimal] = None
    actual_absolute: Optional[Decimal] = None
    actual_per_unit: Optional[Decimal] = None
    difference_absolute: Optional[Decimal] = None   # baseline - actual
    difference_per_unit: Optional[Decimal] = None
    reduction_pct_absolute: Optional[Decimal] = None  # difference / baseline * 100
    reduction_pct_per_unit: Optional[Decimal] = None


class ITMMReportingResponse(DashboardBase):
    """Full response for the ITMM Reporting LCA Module Breakdown tab."""
    declared_unit_value: Optional[Decimal] = None
    declared_unit_type: Optional[str] = None
    rows: List[ITMMModuleRow]


# ─────────────────────────────────────────────────────────────────────────────
# SQL
# Returns one row with per-module Actual and Baseline values.
#
# Structure:
#   TIER 1 — emissions_results JOIN (canonical per-module tCO2e)
#   TIER 2 — extra_fields fallback (B1, B6 non-elec, B7, B8)
#   TIER 3 — stored carbon via view joins
#   TIER 4 — completeness upscaling (placeholder, returns 0)
#   MITIGATION — per-module mitigation contributions that inflate Baseline
#   SHORTCUT DELTAS — base_case minus actual_case from shortcut tables
# ─────────────────────────────────────────────────────────────────────────────

# ITMM totals are aggregated from structured emissions_results facts.

# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/lca-module-breakdown",
    response_model=ITMMReportingResponse,
    summary="ITMM Reporting: LCA module breakdown (Baseline vs Actual)",
)
async def get_ittm_lca_module_breakdown(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> ITMMReportingResponse:
    """
    Returns the ITMM Reporting LCA Module Breakdown table, comparing Baseline
    vs Actual emissions per lifecycle module.

    Each row includes:
    - absolute values (tCO2e)
    - per declared unit values (tCO2e / declared unit), if a declared unit is configured
    - difference (baseline - actual)
    - reduction percentage (difference / baseline × 100)

    Subtotal rows (is_subtotal=True) are computed in Python from their constituent
    module rows and do not have separate SQL columns.

    Electricity emissions respect the ``elec_method`` toggle:
    - 'location' (default): location-based accounting
    - 'market': market-based accounting (GreenPower / RECs)
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    project = await ProjectContextHelper.fetch_project(db, project_id)

    declared_unit_value: Optional[Decimal] = (
        Decimal(str(project.declared_unit_value))
        if project.declared_unit_value is not None
        else None
    )
    declared_unit_type: Optional[str] = project.declared_unit_type

    def _dec(val) -> Decimal:
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    ledger = await aggregate_emissions_results(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        accounting_method=elec_method,
    )
    actual_modules = ledger["modules"]
    baseline_modules = ledger["mitigation_modules"]
    adjustments = ledger["baseline_adjustment"]
    row: dict = {
        "actual_a1a3": actual_modules.get("A1-A3", Decimal(0)),
        "baseline_a1a3": actual_modules.get("A1-A3", Decimal(0)) + baseline_modules.get("A1-A3", Decimal(0)) + adjustments.get("A1-A3", Decimal(0)),
        "actual_a4": actual_modules.get("A4", Decimal(0)),
        "baseline_a4": actual_modules.get("A4", Decimal(0)) + baseline_modules.get("A4", Decimal(0)) + adjustments.get("A4", Decimal(0)),
        "actual_a5_construction": actual_modules.get("A5", Decimal(0)),
        "baseline_a5_construction": actual_modules.get("A5", Decimal(0)) + baseline_modules.get("A5", Decimal(0)) + adjustments.get("A5", Decimal(0)),
        "actual_a5_luc": sum((v for k, v in actual_modules.items() if k == "A5_LUC"), Decimal(0)),
        "baseline_a5_luc": sum((v for k, v in actual_modules.items() if k == "A5_LUC"), Decimal(0)),
        "actual_b1_1": actual_modules.get("B1", Decimal(0)),
        "baseline_b1_1": actual_modules.get("B1", Decimal(0)) + baseline_modules.get("B1", Decimal(0)) + adjustments.get("B1", Decimal(0)),
        "actual_b2_b5": actual_modules.get("B2-5", Decimal(0)),
        "baseline_b2_b5": actual_modules.get("B2-5", Decimal(0)) + baseline_modules.get("B2-5", Decimal(0)) + adjustments.get("B2-5", Decimal(0)),
        "actual_b6": actual_modules.get("B6", Decimal(0)),
        "baseline_b6": actual_modules.get("B6", Decimal(0)) + baseline_modules.get("B6", Decimal(0)) + adjustments.get("B6", Decimal(0)),
        "actual_b7": actual_modules.get("B7", Decimal(0)),
        "baseline_b7": actual_modules.get("B7", Decimal(0)) + baseline_modules.get("B7", Decimal(0)) + adjustments.get("B7", Decimal(0)),
        "actual_b8": actual_modules.get("B8", Decimal(0)),
        "baseline_b8": actual_modules.get("B8", Decimal(0)) + baseline_modules.get("B8", Decimal(0)) + adjustments.get("B8", Decimal(0)),
        "actual_b1_2": Decimal(0),
        "baseline_b1_2": Decimal(0),
    }

    row["biogenic"] = ledger["stored_carbon"]

    actual_a1a3           = _dec(row.get("actual_a1a3"))
    baseline_a1a3         = _dec(row.get("baseline_a1a3"))
    biogenic              = _dec(row.get("biogenic"))
    actual_a4             = _dec(row.get("actual_a4"))
    baseline_a4           = _dec(row.get("baseline_a4"))
    actual_a5_construction  = _dec(row.get("actual_a5_construction"))
    baseline_a5_construction = _dec(row.get("baseline_a5_construction"))
    actual_a5_luc         = _dec(row.get("actual_a5_luc"))
    baseline_a5_luc       = _dec(row.get("baseline_a5_luc"))
    actual_b1_1           = _dec(row.get("actual_b1_1"))
    baseline_b1_1         = _dec(row.get("baseline_b1_1"))
    actual_b2_b5          = _dec(row.get("actual_b2_b5"))
    baseline_b2_b5        = _dec(row.get("baseline_b2_b5"))
    actual_b6             = _dec(row.get("actual_b6"))
    baseline_b6           = _dec(row.get("baseline_b6"))
    actual_b7             = _dec(row.get("actual_b7"))
    baseline_b7           = _dec(row.get("baseline_b7"))
    actual_b8             = _dec(row.get("actual_b8"))
    baseline_b8           = _dec(row.get("baseline_b8"))

    # Subtotals (computed in Python)
    actual_upfront   = actual_a1a3 + actual_a4 + actual_a5_construction + actual_a5_luc
    baseline_upfront = baseline_a1a3 + baseline_a4 + baseline_a5_construction + baseline_a5_luc

    actual_in_use_embodied   = actual_b1_1 + actual_b2_b5
    baseline_in_use_embodied = baseline_b1_1 + baseline_b2_b5

    # B1.2 — Use - operational processes (useB1G2/useB1G3)
    actual_b1_2   = _dec(row.get("actual_b1_2"))
    baseline_b1_2 = _dec(row.get("baseline_b1_2"))

    actual_in_use_operational   = actual_b1_2 + actual_b6 + actual_b7
    baseline_in_use_operational = baseline_b1_2 + baseline_b6 + baseline_b7

    def _make_row(
        code: str,
        label: str,
        actual_abs: Decimal,
        baseline_abs: Decimal,
        is_subtotal: bool = False,
    ) -> ITMMModuleRow:
        """Build one ITMMModuleRow, computing per-unit and percentage columns."""
        du = declared_unit_value

        actual_per: Optional[Decimal] = (
            (actual_abs / du) if du and du != Decimal(0) else None
        )
        baseline_per: Optional[Decimal] = (
            (baseline_abs / du) if du and du != Decimal(0) else None
        )

        diff_abs = baseline_abs - actual_abs
        diff_per: Optional[Decimal] = (
            (baseline_per - actual_per) if (baseline_per is not None and actual_per is not None) else None
        )

        pct_abs: Optional[Decimal] = (
            (diff_abs / baseline_abs * Decimal(100))
            if baseline_abs != Decimal(0) else None
        )
        pct_per: Optional[Decimal] = (
            (diff_per / baseline_per * Decimal(100))
            if (baseline_per is not None and baseline_per != Decimal(0)) else None
        )

        return ITMMModuleRow(
            module_code=code,
            module_label=label,
            is_subtotal=is_subtotal,
            baseline_absolute=baseline_abs,
            baseline_per_unit=baseline_per,
            actual_absolute=actual_abs,
            actual_per_unit=actual_per,
            difference_absolute=diff_abs,
            difference_per_unit=diff_per,
            reduction_pct_absolute=pct_abs,
            reduction_pct_per_unit=pct_per,
        )

    rows: List[ITMMModuleRow] = [
        _make_row(
            "a1_a3_excl_biogenic",
            "Product stage (A1-A3) - excl biogenic carbon",
            actual_a1a3,
            baseline_a1a3,
        ),
        _make_row(
            "a1_a3_biogenic",
            "Product stage (A1-A3) - sequestered biogenic carbon",
            biogenic,
            biogenic,  # same for both
        ),
        _make_row(
            "a4",
            "Transport to site (A4)",
            actual_a4,
            baseline_a4,
        ),
        _make_row(
            "a5_construction",
            "Construction (A5)",
            actual_a5_construction,
            baseline_a5_construction,
        ),
        _make_row(
            "a5_land_use_change",
            "Land use change (A5)",
            actual_a5_luc,
            baseline_a5_luc,
        ),
        _make_row(
            "total_upfront",
            "Total upfront carbon (A1-A5) - excl biogenic carbon",
            actual_upfront,
            baseline_upfront,
            is_subtotal=True,
        ),
        _make_row(
            "b1_1",
            "Use - material emissions and removals (B1.1)",
            actual_b1_1,
            baseline_b1_1,
        ),
        _make_row(
            "b2_b5",
            "Maintenance (B2), Repair (B3), Refurbishment and replacement (B4-B5)",
            actual_b2_b5,
            baseline_b2_b5,
        ),
        _make_row(
            "total_in_use_embodied",
            "Total in-use embodied carbon (B1.1, B2-B5)",
            actual_in_use_embodied,
            baseline_in_use_embodied,
            is_subtotal=True,
        ),
        _make_row(
            "b1_2",
            "Use - operational processes (B1.2)",
            actual_b1_2,
            baseline_b1_2,
        ),
        _make_row(
            "b6",
            "Operational energy (B6)",
            actual_b6,
            baseline_b6,
        ),
        _make_row(
            "b7",
            "Operational water (B7)",
            actual_b7,
            baseline_b7,
        ),
        _make_row(
            "total_in_use_operational",
            "Total in-use operational carbon (B1.2, B6-B7)",
            actual_in_use_operational,
            baseline_in_use_operational,
            is_subtotal=True,
        ),
        _make_row(
            "b8",
            "Users (B8)",
            actual_b8,
            baseline_b8,
        ),
    ]

    return ITMMReportingResponse(
        declared_unit_value=declared_unit_value,
        declared_unit_type=declared_unit_type,
        rows=rows,
    )
