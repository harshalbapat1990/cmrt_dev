# """
# services/detailed_level_calcs_operational_fuel_water.py

# Service for Operational Energy (B6) and Water (B7) - Detailed Level -
# Operations Stage (Fuel and Water ONLY) calculations.

# Excel source: tbl_detailed_level_calcs_operational_fuel_water
# Sheet: MVP - Grade 1234

# Calculation flow
# ----------------
# Input columns (per row):
#     Emissions Category, Emissions Sub-Category, Emissions Source,
#     Unit, Quantity (Unit), Period, Project ID, Notes

# Lookup table (tbl_detailed_level → v_grade34_detailed_level view):
#     Matched by: Jurisdiction × Emissions Category × Emissions Sub-Category
#                 × Emissions Source (× Unit when provided)

# Formula:
#     Quantity Used =
#         IF(Period="Annual Average",
#            Quantity × MIN(operations_end_year - operations_start_year, 50),
#            Quantity)

#     Scope 1 Emissions (tCO2e) =
#         IFERROR(XLOOKUP(jurisdiction+category+sub+source → scope1_factor) × quantity_used, 0)

#     Scope 2 Emissions (tCO2e) = 0   ← hardcoded (placeholder, easy to change)

#     Scope 3 Emissions (tCO2e) =
#         IFERROR(IFNA(IFERROR(XLOOKUP(... → scope3_factor) × quantity_used, 0), 0), "")
#         → effectively: scope3_factor × quantity_used, else 0

#     Emissions (tCO2e) =
#         IF(OR(category="Fuels", category="Electricity"),
#            Scope1 + Scope2 + Scope3,
#            0)

# Factor columns in v_grade34_detailed_level:
#     emission_factor_scope1  — "Scope 1 Emissions Factor (tCO2e/UoM)"
#     emission_factor_scope3  — "Scope 3 Emissions Factor (tCO2e/UoM)"
# """

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper

# Categories for which the total emissions guard is TRUE (matches Excel formula)
_CATEGORIES_WITH_TOTAL = frozenset({"Fuels", "Electricity","Water"})
_MAX_REFERENCE_PERIOD = 50
_ANNUAL_PERIOD_VALUES = frozenset({"annual average", "average annual life", "annual"})
_TOTAL_LIFE_PERIOD_VALUES = frozenset({"total operational life", "total"})


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class DetailedLevelFuelWaterRequest(BaseModel):
    """
    Input for a single row of tbl_detailed_level_calcs_operational_fuel_water.
    """
    jurisdiction: str = Field(
        ...,
        description="Jurisdiction name (e.g. 'Australia'). Corresponds to cell C779 in Excel.",
    )
    emissions_category: str = Field(
        ...,
        description="Emissions category (e.g. 'Fuels', 'Water').",
    )
    emissions_sub_category: str = Field(
        ...,
        description="Emissions sub-category (e.g. 'Liquid Fuels (Static)').",
    )
    emissions_source: str = Field(
        ...,
        description="Emissions source / item name (e.g. 'Diesel oil').",
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measure (e.g. 'kL', 't'). Used to narrow the lookup when provided.",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="Quantity in the stated unit (Quantity (Unit) column).",
    )
    period: str = Field(
        ...,
        description="Period type: 'Annual', 'Annual Average', 'Average Annual Life', 'Total Operational Life', or 'Total' (case-insensitive).",
    )
    project_id: Optional[UUID] = Field(
        None,
        description=(
            "Project ID required when period is 'Annual Average' so operational years can "
            "be used to calculate reference period = MIN(ops_end - ops_start, 50)."
        ),
    )
    notes: Optional[str] = Field(
        None,
        description="Free-text notes — echoed in response, not used in calculation.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "emissions_category": "Fuels",
                "emissions_sub_category": "Liquid Fuels (Static)",
                "emissions_source": "Diesel oil",
                "unit": "kL",
                "quantity": 10.5,
                "period": "Total Operational Life",
                "project_id": "6df1ce4f-7c5f-4950-b99e-0262b9f1fbe6",
                "notes": None,
            }
        }
    }


class DetailedLevelFuelWaterResponse(BaseModel):
    """
    Calculated emissions for one row of the Operational Fuel/Water detailed table.
    """
    # --- Echoed inputs ---
    jurisdiction: str
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    unit: Optional[str]
    quantity: float
    period: str
    project_id: Optional[UUID]
    reference_period_years: Optional[int] = Field(
        None,
        description=(
            "Reference period in years for annual-average calculations: "
            "MIN(operations_end_year - operations_start_year, 50)."
        ),
    )
    quantity_used_for_calculation: float = Field(
        ...,
        description="Quantity after applying period rule (used in emission calculations).",
    )
    notes: Optional[str]

    # --- Factors retrieved from view (for transparency) ---
    scope1_factor_tco2e_per_uom: Optional[float] = Field(
        None,
        description="Scope 1 emission factor (tCO2e/UoM) from v_grade34_detailed_level.",
    )
    scope3_factor_tco2e_per_uom: Optional[float] = Field(
        None,
        description="Scope 3 emission factor (tCO2e/UoM) from v_grade34_detailed_level.",
    )

    # --- Calculated outputs (tCO2e) ---
    scope1_emissions_tco2e: float = Field(
        ...,
        description="Scope 1 Emissions = scope1_factor × quantity (0 when factor not found).",
    )
    scope2_emissions_tco2e: float = Field(
        0.0,
        description="Scope 2 Emissions — always 0 for Fuel/Water (placeholder).",
    )
    scope3_emissions_tco2e: float = Field(
        ...,
        description="Scope 3 Emissions = scope3_factor × quantity (0 when factor not found).",
    )
    total_emissions_tco2e: float = Field(
        ...,
        description=(
            "Total Emissions = Scope1 + Scope2 + Scope3 "
            "when category is 'Fuels' or 'Electricity', else 0."
        ),
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class DetailedLevelFuelWaterCalculator:
    """
    Replicates Excel tbl_detailed_level_calcs_operational_fuel_water formulas.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: DetailedLevelFuelWaterRequest,
    ) -> DetailedLevelFuelWaterResponse:

        period_normalized = self._normalize_period(request.period)
        reference_period = None
        quantity_used = request.quantity

        if period_normalized == "annual average":
            if request.project_id is None:
                raise ValueError("project_id is required when period is 'Annual Average'")

            project = await ProjectContextHelper.fetch_project(db, request.project_id)
            ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
            reference_period = max(0, min(ops_end - ops_start, _MAX_REFERENCE_PERIOD))
            quantity_used = request.quantity * reference_period

        # 1. Fetch emission factors from v_grade34_detailed_level
        scope1_factor, scope3_factor = await self._fetch_factors(db, request)

        # 2. Calculate scope emissions (IFERROR → 0 when factor is None)
        scope1 = (scope1_factor or 0.0) * quantity_used
        scope2 = 0.0  # Hardcoded — placeholder, easy to change
        scope3 = (scope3_factor or 0.0) * quantity_used

        # 3. Apply category guard:
        #    IF(OR(category="Fuels", category="Electricity"), SUM(S1:S3), 0)
        if request.emissions_category in _CATEGORIES_WITH_TOTAL:
            total = scope1 + scope2 + scope3
        else:
            total = 0.0

        return DetailedLevelFuelWaterResponse(
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            unit=request.unit,
            quantity=request.quantity,
            period="Annual Average" if period_normalized == "annual average" else "Total Operational Life",
            project_id=request.project_id,
            reference_period_years=reference_period,
            quantity_used_for_calculation=quantity_used,
            notes=request.notes,
            scope1_factor_tco2e_per_uom=scope1_factor,
            scope3_factor_tco2e_per_uom=scope3_factor,
            scope1_emissions_tco2e=round_result(scope1),
            scope2_emissions_tco2e=scope2,
            scope3_emissions_tco2e=round_result(scope3),
            total_emissions_tco2e=round_result(total),
        )

    @staticmethod
    def _normalize_period(period: str) -> str:
        value = (period or "").strip().lower()
        if value in _ANNUAL_PERIOD_VALUES:
            return "annual average"
        if value in _TOTAL_LIFE_PERIOD_VALUES:
            return "total operational life"
        raise ValueError(
            f"Invalid period '{period}'. Expected one of: 'Annual', 'Annual Average', "
            "'Average Annual Life', 'Total Operational Life', or 'Total'."
        )

    async def _fetch_factors(
        self,
        db: AsyncSession,
        request: DetailedLevelFuelWaterRequest,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Query v_grade34_detailed_level for scope1 and scope3 factors.

        Matches: Jurisdiction × Emissions Category × Emissions Sub-Category
                 × Emissions Source (× UoM when unit is provided).

        When unit is omitted, the first matching row is returned (replicating
        XLOOKUP first-match behaviour).
        """
        unit_clause = 'AND "UoM" = :unit' if request.unit else ""

        sql = f"""
            SELECT
                emission_factor_scope1,
                emission_factor_scope3
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction"          = :jurisdiction
              AND "Emissions Category"    = :emissions_category
              AND "Emissions Sub-Category"= :emissions_sub_category
              AND "Emissions Source"      = :emissions_source
              {unit_clause}
            LIMIT 1
        """
        params: dict = {
            "jurisdiction": request.jurisdiction,
            "emissions_category": request.emissions_category,
            "emissions_sub_category": request.emissions_sub_category,
            "emissions_source": request.emissions_source,
        }
        if request.unit:
            params["unit"] = request.unit

        result = await db.execute(text(sql), params)
        row = result.fetchone()

        if row is None:
            return None, None

        def _to_float(v) -> Optional[float]:
            if v is None:
                return None
            return float(v) if isinstance(v, Decimal) else float(v)

        return _to_float(row.emission_factor_scope1), _to_float(row.emission_factor_scope3)


# Module-level singleton
calculator = DetailedLevelFuelWaterCalculator()
