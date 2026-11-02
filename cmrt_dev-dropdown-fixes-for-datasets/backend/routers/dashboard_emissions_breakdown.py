"""
routers/dashboard_emissions_breakdown.py

Dashboard Results API — Emissions Breakdown

Main chart data for the Carbon Management & Reporting Tool dashboard.

Returns:
  modules          — emissions totals per lifecycle module
  sourceCategories — emissions totals per source category
  summaryIndicators— headline KPI (total gross emissions)

─────────────────────────────────────────────────────────────────────────────
Module allocation rules (from Emissions breakdown.csv)
─────────────────────────────────────────────────────────────────────────────

A1-A3  (Raw material supply, Transport, Manufacturing)
  - asset                               : product_stage_a1a3      [Grade 1 — A1-A3 stage portion]
  - component (Grade 2)                 : product_stage_a1_a3_tco2e from extra_fields (primary);
                                          falls back to "Product Stage (A1-3) (tCO2e/UoM)" × qty
                                          via v_grade2_component_level, then total_emissions_tco2e
  - bcDetailedLevel / constructionG3 /
    recurringG3  where cat='Materials'  : product_stage_a1_a3_tco2e from extra_fields
  - concreteRegSimplified / Detailed    : total_emissions_tco2e
  - shortcutIsMaterials (non-maint.)    : extra_fields->>'actual_case'
  - shortcutSat4p where source =
    'Construction materials'            : actual_scope3 + actual_scope4

A4  (Transport to site)
  - asset                               : transport_a4            [Grade 1 — A4 stage portion]
  - component (Grade 2)                 : transport_stage_a4_tco2e from extra_fields (primary);
                                          falls back to "Transport Stage (A4) (tCO2e/UoM)" × qty
  - bcDetailedLevel / constructionG3 /
    recurringG3  where cat='Materials'  : transport_stage_a4_tco2e from extra_fields
  - shortcutSat4p where source =
    'Transport (construction materials)': actual_scope3 + actual_scope4

A5  (Construction installation process)
  - asset                               : construction_a5         [Grade 1 — A5 stage portion]
  - component (Grade 2)                 : construction_stage_a5_tco2e from extra_fields (primary);
                                          falls back to "Construction Stage (A5) (tCO2e/UoM)" × qty
  - bcDetailedLevel / constructionG3 /
    recurringG3  non-Materials & non-Offset: construction_stage_a5_tco2e (fallback: total_tco2e)
  - electricity                         : location_based_tco2e / market_based_tco2e
  - shortcutSat4p other sources         : actual_scope3 + actual_scope4

B1  (Use)
  - useB1G2, useB1G3                    : total_emissions_tco2e

B2-B5  (Maintenance, Repair, Replacement, Refurbishment)
  - componentRepl, refurbishment,
    replDetailed                        : total_emissions_tco2e

B6  (Operational energy — non-Water)
  - opEnergy                            : location/market_based_total_tco2e
  - opEnergyDetailed where cat≠'Water'  : total_emissions_tco2e
  - opEnergyElectricity                 : location/market_based_tco2e

B7  (Water)
  - opEnergyDetailed where cat='Water'  : total_emissions_tco2e

B8  (Users)
  - roadUsers, railUsers                : total_emissions_tco2e  (small projects)
  - largeRoadUsers, largeRoadParams,
    largeRailUsers                      : total_emissions_tco2e  (large projects)

Offsets  (NOT included in A1–B8 totals; returned as negative value)
  - bcDetailedLevel / constructionG3 /
    recurringG3 / replDetailed /
    opEnergyDetailed  where cat='Offset': total_emissions_tco2e

Stored carbon  (returned as negative value)
  - component (Grade 2)                 : "Carbon Storage (tCO2e/UoM)" × qty via
                                          v_grade2_component_level join
  - bcDetailedLevel (Grade 3/4)         : "Carbon Storage (tCO2e/UoM)" × qty via
                                          v_grade34_detailed_level join (5-key incl. Sub-Category)

─────────────────────────────────────────────────────────────────────────────
Query params
─────────────────────────────────────────────────────────────────────────────
  project_id        UUID  required
  stage_instance_id UUID  required
  elec_method       str   optional — 'location' (default) | 'market'
  jurisdiction      str   resolved automatically from project → organisation → jurisdiction
                            (falls back to 'Australia' if not configured)

─────────────────────────────────────────────────────────────────────────────
Completeness upscaling adjustment
─────────────────────────────────────────────────────────────────────────────
  Uplift rows stored in activity_data with ui_table_key = 'completeness':
    extra_fields->>'module'                    'a1_a3' | 'a4' | 'a5' | 'b1' | 'b2_b5' | 'b6' | 'b7'
    extra_fields->>'upscaling_adjustment_tco2e' additive tCO2e adjustment
  CTEs uplift_a1a3 … uplift_b7 are wired into the final SELECT.
  Applies to: A1-A3, A4, A5, B1, B2-B5, B6, B7 (NOT B8, Offsets, Stored carbon).
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from services.emissions_result_aggregates import aggregate_emissions_results
from services.project_context_helper import ProjectContextHelper

router = APIRouter(
    prefix="/api/dashboard/emissions-breakdown",
    tags=["Dashboard - Emissions Breakdown"],
)

# Compatibility query for carbon-valuation routers. This keeps their existing
# row shape while sourcing every emissions amount from the canonical ledger.
_MODULE_SQL = text("""
    SELECT
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'A1-A3' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS a1_a3,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'A4' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS a4,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'A5' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS a5,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'B1' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS b1,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'B2-5' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS b2_b5,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'B6' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS b6,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'B7' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS b7,
        COALESCE(SUM(CASE WHEN er.lifecycle_module_code = 'B8' AND er.reporting_measure = 'actual' THEN er.value END), 0) AS b8,
        COALESCE(SUM(CASE WHEN er.reporting_measure = 'offset' THEN -ABS(er.value) END), 0) AS offsets,
        COALESCE(SUM(CASE WHEN er.reporting_measure = 'stored_carbon' THEN er.value END), 0) AS stored_carbon
    FROM emissions_results er
    JOIN activity_data ad ON ad.id = er.activity_data_id
    WHERE er.project_id = CAST(:project_id AS uuid)
      AND er.project_stage_instance_id = CAST(:stage_instance_id AS uuid)
      AND ad.project_id = er.project_id
      AND ad.project_stage_instance_id = er.project_stage_instance_id
      AND (CAST(:project_option_id AS uuid) IS NULL OR ad.project_option_id = CAST(:project_option_id AS uuid))
      AND (CAST(:submission_period_id AS uuid) IS NULL OR ad.submission_period_id = CAST(:submission_period_id AS uuid))
      AND (
          er.accounting_basis = 'common'
          OR (:elec_method = 'location' AND er.accounting_basis = 'location')
          OR (:elec_method = 'market' AND er.accounting_basis = 'market')
      )
      AND er.is_supplementary IS FALSE
""")


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class ModuleRow(DashboardBase):
    """Emissions total for one lifecycle module."""
    code: str       # e.g. "A1", "A4", "A5", "B1", "B2", "B6", "B7", "B8", "Offsets", "Stored carbon"
    label: str      # Display label shown in the table / chart
    value: Decimal  # tCO2e (negative for Offsets and Stored carbon)


class SourceCategoryRow(DashboardBase):
    """Emissions total for one source category."""
    category: str   # e.g. "Materials", "Electricity", "Fuels", "Gases", "Waste"
    value: Decimal  # tCO2e


class SummaryIndicator(DashboardBase):
    value: Decimal
    unit: str


class SummaryIndicators(DashboardBase):
    primaryIndicator: Optional[SummaryIndicator] = None    # Upfront intensity per declared unit (A1-A5 / declared unit)
    secondaryIndicator: Optional[SummaryIndicator] = None  # Upfront intensity per CAPEX ($M) (A1-A5 / $M)


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


# ─────────────────────────────────────────────────────────────────────────────
# Module and category totals are aggregated from emissions_results through the shared ledger service.

# Module metadata: display labels and ordering
# ─────────────────────────────────────────────────────────────────────────────

_MODULE_META = [
    # (code, label, sql_column)
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
# Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=EmissionsBreakdownResponse,
    summary="Emissions breakdown by module and source category",
)
async def get_emissions_breakdown_summary(
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

    The jurisdiction is resolved automatically from the project's proponent organisation.
    Grade 2 component-level emissions are split into A1-A3 / A4 / A5 by joining to
    v_grade2_component_level using the resolved jurisdiction.

    Grade 3/4 Materials rows are split into A1-A3 (scope3_ef × qty) and A4 (residual)
    by joining to v_grade34_detailed_level.
    """
    if elec_method not in ("location", "market"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="elec_method must be 'location' or 'market'",
        )

    # Resolve jurisdiction from project → organisation → jurisdiction
    ledger = await aggregate_emissions_results(
        db,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        project_option_id=project_option_id,
        submission_period_id=submission_period_id,
        accounting_method=elec_method,
    )
    module_values = ledger["modules"]
    module_map = {
        "A1-A3": "A1-A3", "A4": "A4", "A5": "A5", "B1": "B1",
        "B2-5": "B2-5", "B6": "B6", "B7": "B7", "B8": "B8",
    }
    mod_row = {
        "a1_a3": module_values.get("A1-A3", Decimal(0)),
        "a4": module_values.get("A4", Decimal(0)),
        "a5": module_values.get("A5", Decimal(0)),
        "b1": module_values.get("B1", Decimal(0)),
        "b2_b5": module_values.get("B2-5", Decimal(0)),
        "b6": module_values.get("B6", Decimal(0)),
        "b7": module_values.get("B7", Decimal(0)),
        "b8": module_values.get("B8", Decimal(0)),
        "offsets": module_values.get("Offsets", Decimal(0)),
        "stored_carbon": ledger["stored_carbon"],
    }

    def _dec(val) -> Decimal:
        """Coerce a DB numeric value to Decimal, defaulting to 0."""
        if val is None:
            return Decimal(0)
        return Decimal(str(val))

    modules: List[ModuleRow] = []
    for code, label, col in _MODULE_META:
        if col is None:
            # Placeholder code (e.g. A2, A3, B3-B5) — always zero, kept for frontend ordering
            modules.append(ModuleRow(code=code, label=label, value=Decimal(0)))
        else:
            modules.append(ModuleRow(code=code, label=label, value=_dec(mod_row[col])))

    source_categories: List[SourceCategoryRow] = [
        SourceCategoryRow(
            category=category,
            value=_dec(value),
        )
        for category, value in sorted(ledger["categories"].items(), key=lambda item: item[1], reverse=True)
        if value > 0
    ]

    # ── Summary indicators ───────────────────────────────────────────────────
    # Headline metrics are upfront emissions intensity values (A1-A5).
    project = await ProjectContextHelper.fetch_project(db, project_id)
    upfront_a1_a5_total = _dec(mod_row["a1_a3"]) + _dec(mod_row["a4"]) + _dec(mod_row["a5"])

    declared_unit_value = (
        Decimal(str(project.declared_unit_value))
        if project.declared_unit_value is not None
        else None
    )
    declared_unit_type = (project.declared_unit_type or "").strip()

    project_capex_million = (
        Decimal(str(project.project_capex_million))
        if project.project_capex_million is not None
        else None
    )

    primary_indicator: Optional[SummaryIndicator] = None
    if declared_unit_value is not None and declared_unit_value != 0 and declared_unit_type:
        primary_indicator = SummaryIndicator(
            value=upfront_a1_a5_total / declared_unit_value,
            unit=f"tCO\u2082e/{declared_unit_type}",
        )

    secondary_indicator: Optional[SummaryIndicator] = None
    if project_capex_million is not None and project_capex_million != 0:
        secondary_indicator = SummaryIndicator(
            value=upfront_a1_a5_total / project_capex_million,
            unit="tCO\u2082e/$M",
        )

    summary_indicators = SummaryIndicators(
        primaryIndicator=primary_indicator,
        secondaryIndicator=secondary_indicator,
    )

    return EmissionsBreakdownResponse(
        modules=modules,
        sourceCategories=source_categories,
        summaryIndicators=summary_indicators,
    )
