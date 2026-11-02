"""
routers/dashboard_mitigation_summary.py

Dashboard Results API — Mitigation Summary (Waterfall Chart)

Returns a waterfall chart dataset for Large projects showing how the project
moves from Base Case emissions down to Actual Case through three mitigation
categories.

─────────────────────────────────────────────────────────────────────────────
Waterfall bars (in order)
─────────────────────────────────────────────────────────────────────────────

  Base case            — total column (highest bar)
                         = Actual case + Avoidance/reduction + Substitution + Other
                           (re-adds the savings so it represents pre-mitigation total)

  Avoidance/reduction  — step (negative): sum of emissions from all
                         activity_data rows whose ui_table_key ends with
                         '-mitigation' (but NOT '-mitigation-subst-*').
                         These rows are linked to project_mitigations with
                         mitigation_type = 'Avoidance/reduction'.

  Substitution         — step (negative): net savings from material substitution.
                         = SUM(replaced leg rows) − SUM(adopted leg rows)
                         ui_table_key ends with '-mitigation-subst-replaced'
                         or '-mitigation-subst-adopted'.
                         Includes manually entered and auto-calculated BAU
                         substitution mitigations.

  Other                — step (negative): difference between base-case and
                         actual-case emissions stored in the 'other tool
                         shortcut' data entry tables (shortcutIsMaterials,
                         shortcutSat4p). These rows carry both base and
                         actual values in extra_fields.

  Actual case          — total column: total gross A1–B8 emissions for the
                         submission, respecting the elec_method toggle for
                         electricity tables.

─────────────────────────────────────────────────────────────────────────────
Sign convention
─────────────────────────────────────────────────────────────────────────────
  - Base case and Actual case → positive tCO₂e totals
  - Avoidance/reduction, Substitution, Other → negative (represent reductions)
  - All savings are positive internally; negated before returning

─────────────────────────────────────────────────────────────────────────────
Mitigation ui_table_key patterns
─────────────────────────────────────────────────────────────────────────────
  '<base_key>-mitigation'               → Avoidance/reduction
  '<base_key>-mitigation-subst-adopted' → Substitution (adopted/new material)
  '<base_key>-mitigation-subst-replaced'→ Substitution (replaced/old material)

  Where <base_key> is any of the standard table keys:
    asset, component, bcDetailedLevel, electricity,
    useB1G2, useB1G3, componentRepl, refurbishment, replDetailed,
    opEnergy, opEnergyDetailed, opEnergyElectricity,
    largeRoadParams, largeRoadUsers, largeRailUsers, roadUsers, railUsers,
    concreteRegSimplified, concreteRegDetailed

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
    prefix="/api/dashboard/mitigation-summary",
    tags=["Dashboard - Mitigation Summary"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class WaterfallBar(DashboardBase):
    """One bar in the waterfall chart."""
    label: str
    value: Decimal
    type: str  # 'total' | 'step'


class MitigationSummarySummary(DashboardBase):
    """Flat summary of the five waterfall values (tCO₂e)."""
    base_case_tco2e: Decimal
    avoidance_reduction_tco2e: Decimal   # negative
    substitution_tco2e: Decimal          # negative
    other_tco2e: Decimal                 # negative
    actual_case_tco2e: Decimal


class MitigationSummaryResponse(DashboardBase):
    """
    Full response for the Mitigation Summary dashboard tab.

    chart   → drives the waterfall chart (five ordered bars)
    summary → flat summary for table / KPI display
    unit    → 'tCO2e'
    """
    unit: str = "tCO2e"
    chart: List[WaterfallBar]
    summary: MitigationSummarySummary


# ─────────────────────────────────────────────────────────────────────────────
# SQL — mitigation components
#
# Returns three savings values in a single row:
#   avoidance_savings    — total tCO₂e from '-mitigation' rows (positive = saved)
#   substitution_savings — net tCO₂e saved by substitution
#                          = SUM(replaced legs) − SUM(adopted legs)
#   other_savings        — net tCO₂e saved from shortcut tables
#                          = MAX(0, base − actual) for shortcutIsMaterials
#                          + MAX(0, base − actual) for shortcutSat4p
# ─────────────────────────────────────────────────────────────────────────────

# Mitigation totals are aggregated from structured emissions_results facts.

# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=MitigationSummaryResponse,
    summary="Mitigation summary waterfall chart data",
)
async def get_mitigation_summary(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> MitigationSummaryResponse:
    """
    Returns waterfall chart data for the Mitigation Summary dashboard tab.

    The five bars are:
      1. Base case     — total gross emissions before any mitigations (positive)
      2. Avoidance/reduction — emissions reduced via avoidance initiatives (negative step)
      3. Substitution  — net emissions saved by material substitution (negative step)
      4. Other         — emissions difference from shortcut tool tables (negative step)
      5. Actual case   — total gross A1–B8 emissions after mitigations (positive)

    Base case = Actual case + |Avoidance/reduction| + |Substitution| + |Other|

    Electricity emissions respect the `elec_method` toggle:
      - 'location' (default): location-based electricity accounting
      - 'market': market-based electricity accounting (GreenPower / RECs)
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    # ── Guard: LARGE projects, DESIGN and CONSTRUCTION stages only ────────────
    _guard = await db.execute(
        text("""
            SELECT p.project_class, psi.stage
            FROM project p
            CROSS JOIN project_stage_instances psi
            WHERE p.id   = CAST(:project_id        AS uuid)
              AND psi.id = CAST(:stage_instance_id AS uuid)
        """),
        {"project_id": str(project_id), "stage_instance_id": str(stage_instance_id)},
    )
    _guard_row = _guard.fetchone()

    if _guard_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or stage instance not found",
        )
    if _guard_row[0] != "LARGE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mitigation Summary is only available for LARGE projects",
        )
    if _guard_row[1] == "BUSINESS CASE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mitigation Summary is only available for the DESIGN and CONSTRUCTION stage",
        )

    def _dec(val) -> Decimal:
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    # ── Mitigation components (includes actual_case calculation) ────────────────────────────
    mit_params = {
        "project_id":           str(project_id),
        "stage_instance_id":    str(stage_instance_id),
        "project_option_id":    str(project_option_id)    if project_option_id    else None,
        "submission_period_id": str(submission_period_id) if submission_period_id else None,
    }

    ledger = await aggregate_emissions_results(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        accounting_method=elec_method,
    )
    mitigation_values = ledger["mitigation"]
    avoidance_savings = sum(
        (value for key, value in mitigation_values.items()
         if key.endswith("-mitigation") and "-mitigation-subst-" not in key),
        Decimal(0),
    )
    replaced = sum((value for key, value in mitigation_values.items() if key.endswith("-mitigation-subst-replaced")), Decimal(0))
    adopted = sum((value for key, value in mitigation_values.items() if key.endswith("-mitigation-subst-adopted")), Decimal(0))
    substitution_savings = max(Decimal(0), replaced - adopted)
    other_savings = sum(ledger["baseline_adjustment"].values(), Decimal(0))
    reportable_modules = {"A1-A3", "A4", "A5", "B1", "B2-5", "B6", "B7", "B8"}
    actual_case = sum(
        (value for module, value in ledger["modules"].items() if module in reportable_modules),
        Decimal(0),
    )

    # Step values are negative (savings reduce emissions)
    avoidance_step:    Decimal = -avoidance_savings
    substitution_step: Decimal = -substitution_savings
    other_step:        Decimal = -other_savings

    # Base case = actual case re-adding all savings
    base_case: Decimal = actual_case + avoidance_savings + substitution_savings + other_savings

    # ── Waterfall chart ──────────────────────────────────────────────────────
    chart: List[WaterfallBar] = [
        WaterfallBar(label="Base case",            value=base_case,         type="total"),
        WaterfallBar(label="Avoidance / reduction",value=avoidance_step,    type="step"),
        WaterfallBar(label="Substitution",         value=substitution_step, type="step"),
        WaterfallBar(label="Other",                value=other_step,        type="step"),
        WaterfallBar(label="Actual case",          value=actual_case,       type="total"),
    ]

    summary = MitigationSummarySummary(
        base_case_tco2e=base_case,
        avoidance_reduction_tco2e=avoidance_step,
        substitution_tco2e=substitution_step,
        other_tco2e=other_step,
        actual_case_tco2e=actual_case,
    )

    return MitigationSummaryResponse(chart=chart, summary=summary)
