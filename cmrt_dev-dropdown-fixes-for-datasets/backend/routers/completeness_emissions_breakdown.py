"""Completeness summary and emissions upscaling endpoints.

All base emissions totals come from emissions_results. Activity rows provide report filters and descriptive source-category fallback. Completeness uplift inputs remain stored on activity rows and are applied to ledger totals.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import Field
from services._calc_utils import DashboardBase
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.completeness_emissions_ledger import get_completeness_emissions_totals

router = APIRouter(
    prefix="/api/dashboard/completeness-emissions-breakdown",
    tags=["Dashboard - Completeness Emissions Breakdown"],
)

COMPLETENESS_MODULE_DEFS = [
    ("a1_a3", "A1-A3", "a1_a3"),
    ("a4", "A4", "a4"),
    ("a5", "A5", "a5"),
    ("b1", "B1", "b1"),
    ("b2_b5", "B2-B5", "b2_b5"),
    ("b6", "B6", "b6"),
    ("b7", "B7", "b7"),
]

COMPLETENESS_MIN_PCT = Decimal("80")
COMPLETENESS_MAX_PCT = Decimal("100")


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ModuleRow(DashboardBase):
    """Emissions total for one lifecycle module."""
    code: str       # e.g. "A1", "A4", "A5", "B1", "B2", "B6", "B7", "B8", "Offsets", "Stored carbon"
    label: str      # Display label shown in the table / chart
    value: Decimal  # tCO2e (negative for Offsets)


class SourceCategoryRow(DashboardBase):
    """Emissions total for one source category."""
    category: str   # e.g. "Materials", "Electricity", "Fuels", "Gases", "Waste"
    value: Decimal  # tCO2e


class SummaryIndicator(DashboardBase):
    value: Decimal
    unit: str


class SummaryIndicators(DashboardBase):
    primaryIndicator: Optional[SummaryIndicator] = None    # Total gross A1–B8 emissions
    secondaryIndicator: Optional[SummaryIndicator] = None  # Reserved for future intensity metric


class ModuleCompletenessInput(DashboardBase):
    module: str
    completeness_pct: Decimal = Field(..., ge=80, le=100)


class CalculateRequest(DashboardBase):
    project_id: UUID
    stage_instance_id: UUID
    project_option_id: Optional[UUID] = None
    submission_period_id: Optional[UUID] = None
    elec_method: str = "location"
    modules: List[ModuleCompletenessInput]


class ModuleCalculationResult(DashboardBase):
    module: str
    label: str
    completeness_pct: Decimal
    base_emissions_tco2e: Decimal
    upscaling_adjustment_tco2e: Decimal


class CalculateResponse(DashboardBase):
    modules: List[ModuleCalculationResult]
    total_uplift_tco2e: Decimal


class EmissionsBreakdownResponse(DashboardBase):
    """
    Full response for the Emissions Breakdown dashboard tab.

    modules          → drives the 'Emissions breakdown by module' table and doughnut chart
    sourceCategories → drives the 'Emissions breakdown by source category' table / treemap
    summaryIndicators→ headline KPIs (total emissions, optional intensity)
    """
    modules: List[ModuleRow]
    sourceCategories: List[SourceCategoryRow]
    summaryIndicators: Optional[SummaryIndicators] = None


# Module totals and source categories are read from emissions_results.

_MODULE_META = [
    # (display code, label, result-total field)
    # A1-A3 combined — reported under code "A1"; A2 and A3 are returned as zero
    # so the frontend can display all three slots if needed.
    ("A1",            "A1-A3 Raw material supply, transport & manufacturing", "a1_a3"),
    ("A2",            "A2 (included in A1-A3)",                              None),
    ("A3",            "A3 (included in A1-A3)",                              None),
    ("A4",            "A4 Transport to site",                                "a4"),
    ("A5",            "A5 Construction installation process",                "a5"),
    ("B1",            "B1 Use",                                              "b1"),
    # B2-B5 combined — reported under code "B2"
    ("B2",            "B2-B5 Maintenance, repair, replacement & refurbishment", "b2_b5"),
    ("B3",            "B3 (included in B2-B5)",                              None),
    ("B4",            "B4 (included in B2-B5)",                              None),
    ("B5",            "B5 (included in B2-B5)",                              None),
    ("B6",            "B6 Operational energy use",                           "b6"),
    ("B7",            "B7 Operational water use",                            "b7"),
    ("B8",            "B8 Users",                                            "b8"),
    ("Offsets",       "Offsets",                                             "offsets"),
    ("Stored carbon", "Stored carbon",                                       "stored_carbon"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dec(val) -> Decimal:
    if val is None:
        return Decimal(0)
    return Decimal(str(val))


def _round_emissions(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


async def _fetch_base_module_row(
    db: AsyncSession,
    *,
    project_id: UUID,
    stage_instance_id: UUID,
    project_option_id: Optional[UUID],
    submission_period_id: Optional[UUID],
    elec_method: str,
) -> dict:
    totals = await get_completeness_emissions_totals(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        accounting_method=elec_method,
    )
    mod_row = {key: Decimal(0) for key in (
        "a1_a3", "a4", "a5", "b1", "b2_b5", "b6", "b7", "b8",
        "offsets", "stored_carbon",
    )}
    mod_row.update(totals["modules"])
    mod_row["source_categories"] = totals["source_categories"]
    return mod_row


def _compute_uplift(base_emissions: Decimal, completeness_pct: Decimal) -> Decimal:
    pct_decimal = completeness_pct / Decimal(100)
    if pct_decimal <= 0:
        return Decimal(0)
    uplift_factor = (Decimal(1) / pct_decimal) - Decimal(1)
    return _round_emissions(base_emissions * uplift_factor)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=EmissionsBreakdownResponse,
    summary="Base emissions breakdown by module (pre-completeness uplift)",
)
async def get_completeness_base_summary(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Project stage instance UUID"),
    elec_method:          str  = Query("location", description="Electricity accounting: 'location' or 'market'"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
) -> EmissionsBreakdownResponse:
    """
    Returns emissions broken down by lifecycle module (A1-A3 … B8, Offsets, Stored carbon)
    and by source category (Materials, Electricity, Fuels, etc.) for the specified
    project stage instance.

    Electricity emissions are reported using the `elec_method` parameter:
      - 'location' (default): location-based accounting
      - 'market': market-based accounting (reflects renewable energy purchases / GreenPower)

    Emissions amounts and reporting measures are read from the results ledger.
    Activity rows are used only to apply the selected context and classify legacy
    result facts whose source category is not populated.
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    # ── Module totals ────────────────────────────────────────────────────────
    mod_row = await _fetch_base_module_row(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        elec_method=elec_method,
    )

    modules: List[ModuleRow] = []
    for code, label, col in _MODULE_META:
        if col is None:
            # Placeholder code (e.g. A2, A3, B3-B5) — always zero, kept for frontend ordering
            modules.append(ModuleRow(code=code, label=label, value=Decimal(0)))
        else:
            modules.append(ModuleRow(code=code, label=label, value=_dec(mod_row[col])))

    # ── Source categories ────────────────────────────────────────────────────
    source_categories: List[SourceCategoryRow] = [
        SourceCategoryRow(
            category=category,
            value=value,
        )
        for category, value in mod_row["source_categories"].items()
    ]

    # ── Summary indicators ───────────────────────────────────────────────────
    # Primary indicator: total gross A1-B8 emissions (excludes Offsets and Stored carbon)
    gross_total = sum(
        _dec(mod_row[col])
        for _, _, col in _MODULE_META
        if col is not None and col not in ("offsets", "stored_carbon")
    )
    summary_indicators = SummaryIndicators(
        primaryIndicator=SummaryIndicator(value=gross_total, unit="tCO\u2082e"),
    )

    return EmissionsBreakdownResponse(
        modules=modules,
        sourceCategories=source_categories,
        summaryIndicators=summary_indicators,
    )


@router.post(
    "/calculate",
    response_model=CalculateResponse,
    summary="Calculate completeness upscaling adjustments (tCO2e) per module",
)
async def calculate_completeness_uplift(
    payload: CalculateRequest = Body(...),
    db: AsyncSession = Depends(get_session),
) -> CalculateResponse:
    if payload.elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    allowed_modules = {m[0] for m in COMPLETENESS_MODULE_DEFS}
    for item in payload.modules:
        if item.module not in allowed_modules:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid module '{item.module}'. Allowed: {sorted(allowed_modules)}",
            )
        if item.completeness_pct < COMPLETENESS_MIN_PCT or item.completeness_pct > COMPLETENESS_MAX_PCT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Allowed range is between 80 to 100",
            )

    mod_row = await _fetch_base_module_row(
        db,
        project_id=payload.project_id,
        stage_instance_id=payload.stage_instance_id,
        project_option_id=payload.project_option_id,
        submission_period_id=payload.submission_period_id,
        elec_method=payload.elec_method,
    )
    pct_by_module = {item.module: item.completeness_pct for item in payload.modules}

    results: List[ModuleCalculationResult] = []
    total_uplift = Decimal(0)

    for module_key, label, sql_col in COMPLETENESS_MODULE_DEFS:
        completeness_pct = pct_by_module.get(module_key, COMPLETENESS_MIN_PCT)
        base = _dec(mod_row.get(sql_col))
        uplift = _compute_uplift(base, completeness_pct)
        total_uplift += uplift
        results.append(
            ModuleCalculationResult(
                module=module_key,
                label=label,
                completeness_pct=completeness_pct,
                base_emissions_tco2e=_round_emissions(base),
                upscaling_adjustment_tco2e=uplift,
            )
        )

    return CalculateResponse(
        modules=results,
        total_uplift_tco2e=_round_emissions(total_uplift),
    )
