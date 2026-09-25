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

_MITIGATION_SQL = text("""
WITH

-- ── Avoidance/reduction: keys ending exactly with '-mitigation' ────────────────────────────
-- Excludes substitution legs ('-mitigation-subst-*').
-- total_emissions_tco2e in these rows represents emissions saved.
avoidance AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key LIKE '%-mitigation'
      AND ui_table_key NOT LIKE '%-mitigation-subst-%'
),

-- ── Substitution — replaced leg (old/BAU material, higher emissions) ────────────────────────
subst_replaced AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key LIKE '%-mitigation-subst-replaced'
),

-- ── Substitution — adopted leg (new material, lower emissions) ────────────────────────────
subst_adopted AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key LIKE '%-mitigation-subst-adopted'
),

-- ── Other: shortcutIsMaterials — base_case vs actual_case ─────────────────────────────────
-- base_case = extra_fields->>'base_case'
-- actual    = extra_fields->>'actual_case'
-- savings   = MAX(0, base - actual)
other_shortcut_mat AS (
    SELECT COALESCE(SUM(
        GREATEST(0,
            COALESCE(NULLIF(NULLIF(extra_fields->>'base_case', ''), '-')::numeric, 0) -
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_case', ''), '-')::numeric, 0)
        )
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutIsMaterials'
      AND (extra_fields->>'row_type' IS DISTINCT FROM 'maintenance')
),

-- ── Other: shortcutSat4p — base vs actual ─────────────────────────────────────────────────
-- base   = base_scope1 + base_scope2  (pre-mitigation BAU emissions)
-- actual = actual_scope3 + actual_scope4  (post-mitigation actual emissions)
-- savings = MAX(0, base - actual)
other_sat4p AS (
    SELECT COALESCE(SUM(
        GREATEST(0,
            COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope1', ''), '-')::numeric, 0) +
            COALESCE(NULLIF(NULLIF(extra_fields->>'base_scope2', ''), '-')::numeric, 0) -
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope3', ''), '-')::numeric, 0) -
            COALESCE(NULLIF(NULLIF(extra_fields->>'actual_scope4', ''), '-')::numeric, 0)
        )
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key = 'shortcutSat4p'
),

-- ── Actual case: sum of total emissions EXCLUDING all mitigation rows ────────────────────────
-- This is the gross emissions for the project submission (non-mitigated).
-- Includes: asset, component, electricity, etc. but NOT rows ending with '-mitigation' or '-mitigation-subst-*'
actual_case_total AS (
    SELECT COALESCE(SUM(
        COALESCE(NULLIF(NULLIF(extra_fields->>'total_emissions_tco2e', ''), '-')::numeric, 0)
    ), 0) AS val
    FROM activity_data
    WHERE project_id                 = :project_id
      AND project_stage_instance_id  = :stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND ui_table_key NOT LIKE '%-mitigation'
      AND ui_table_key NOT LIKE '%-mitigation-subst-%'
)

SELECT
    (SELECT val FROM avoidance)                                                   AS avoidance_savings,
    GREATEST(0, (SELECT val FROM subst_replaced) - (SELECT val FROM subst_adopted)) AS substitution_savings,
    (SELECT val FROM other_shortcut_mat) + (SELECT val FROM other_sat4p)          AS other_savings,
    (SELECT val FROM actual_case_total)                                           AS actual_case_emissions
""")


# ─────────────────────────────────────────────────────────────────────────────
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

    # Fetch jurisdiction from project context (needed if filtering by jurisdiction is required)
    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)

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

    mit_result = await db.execute(_MITIGATION_SQL, mit_params)
    mit_row    = mit_result.mappings().fetchone()

    # Extract all values from the mitigation SQL (now includes actual_case)
    avoidance_savings:    Decimal = _dec(mit_row["avoidance_savings"])     if mit_row else Decimal(0)
    substitution_savings: Decimal = _dec(mit_row["substitution_savings"])  if mit_row else Decimal(0)
    other_savings:        Decimal = _dec(mit_row["other_savings"])         if mit_row else Decimal(0)
    actual_case:          Decimal = _dec(mit_row["actual_case_emissions"]) if mit_row else Decimal(0)

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
