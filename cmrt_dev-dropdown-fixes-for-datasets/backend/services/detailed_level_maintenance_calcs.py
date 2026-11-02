# """
# Detailed Level Maintenance (B1) Emissions Calculations

# Calculates Scope 1 and Scope 3 emissions for maintenance activities during operations.

# Formula (per row in tbl_detailed_level_calcs_maintenance52):
# - Scope 1 = Scope1_Factor × IFS(Period="Annual"→Reference_Period×Quantity, "Total Operational Life"→Quantity)
# - Scope 3 = Scope3_Factor × IFS(Period="Annual"→Reference_Period×Quantity, "Total Operational Life"→Quantity)
# - Total = Scope 1 + Scope 3

# Data sources:
# - v_grade34_detailed_level: Scope 1 and Scope 3 emission factors
# """

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from services._calc_utils import round_result


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_YEAR = 1900
_MAX_YEAR = 2200
_MAX_REFERENCE_PERIOD = 50


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------

class DetailedMaintenanceRequest(BaseModel):
    """Calculate Scope 1/3 emissions for a single B1 maintenance row."""

    jurisdiction: str = Field(
        ...,
        description="Jurisdiction (e.g. 'Australia')",
    )
    ops_start: int = Field(
        ...,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations start year (e.g. 2029)",
    )
    ops_end: int = Field(
        ...,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations end year (e.g. 2100)",
    )

    # Row data
    emissions_category: str = Field(
        ...,
        description="Emissions Category (e.g. 'Refrigerants')",
    )
    emissions_sub_category: str = Field(
        ...,
        description="Emissions Sub-Category (e.g. 'HCFCs')",
    )
    emissions_source: str = Field(
        ...,
        description="Emissions Source (e.g. 'HCFC-141b')",
    )
    period: str = Field(
        ...,
        description="Period type: 'Annual' or 'Total Operational Life'",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement (e.g. 'kg', 't')",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="Quantity in the specified unit",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "ops_start": 2029,
                "ops_end": 2100,
                "emissions_category": "Refrigerants",
                "emissions_sub_category": "HCFCs",
                "emissions_source": "HCFC-141b",
                "period": "Annual",
                "unit": "kg",
                "quantity": 100.0,
            }
        }
    }


class DetailedMaintenanceRowResponse(BaseModel):
    """Calculated emissions for one maintenance row."""

    # Echo inputs
    jurisdiction: str
    ops_start: int
    ops_end: int
    reference_period: int = Field(
        ..., description="MIN(ops_end - ops_start, 50) — reference period in years"
    )
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    period: str
    unit: str
    quantity: float

    # Factors retrieved from lookups
    scope1_factor_tco2e_per_uom: Optional[float] = Field(
        None,
        description="Scope 1 Emissions Factor (tCO2e/UoM) from v_grade34_detailed_level",
    )
    scope3_factor_tco2e_per_uom: Optional[float] = Field(
        None,
        description="Scope 3 Emissions Factor (tCO2e/UoM) from v_grade34_detailed_level",
    )

    # Calculated outputs
    scope1_emissions_tco2e: Optional[float] = Field(
        None,
        description="Scope 1 Emissions (tCO2e)",
    )
    scope3_emissions_tco2e: Optional[float] = Field(
        None,
        description="Scope 3 Emissions (tCO2e)",
    )
    total_emissions_tco2e: Optional[float] = Field(
        None,
        description="Total Emissions = Scope 1 + Scope 3 (tCO2e)",
    )


# Alias for backwards compatibility
DetailedMaintenanceResponse = DetailedMaintenanceRowResponse


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class DetailedMaintenanceCalculator:
    """Computes Scope 1 and Scope 3 maintenance emissions for row(s)."""

    async def calculate(
        self,
        db: AsyncSession,
        request: DetailedMaintenanceRequest,
    ) -> DetailedMaintenanceRowResponse:
        """
        Calculate maintenance emissions for a single row in the request.
        """
        # 1. Calculate reference period
        reference_period = min(request.ops_end - request.ops_start, _MAX_REFERENCE_PERIOD)

        # 2. Fetch Scope 1 factor
        scope1_factor = await self._fetch_factor(
            db,
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            scope_field="emission_factor_scope1",
        )

        # 3. Fetch Scope 3 factor
        scope3_factor = await self._fetch_factor(
            db,
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            scope_field="emission_factor_scope3",
        )

        # 4. Calculate quantities based on Period type
        annual_quantity = (
            reference_period * request.quantity
            if request.period.lower() == "annual"
            else request.quantity
        )

        # 5. Calculate emissions
        scope1_emissions = None
        scope3_emissions = None
        total_emissions = None

        if scope1_factor is not None:
            scope1_emissions = scope1_factor * annual_quantity

        if scope3_factor is not None:
            scope3_emissions = scope3_factor * annual_quantity

        if scope1_emissions is not None and scope3_emissions is not None:
            total_emissions = scope1_emissions + scope3_emissions
        elif scope1_emissions is not None:
            total_emissions = scope1_emissions
        elif scope3_emissions is not None:
            total_emissions = scope3_emissions

        return DetailedMaintenanceRowResponse(
            jurisdiction=request.jurisdiction,
            ops_start=request.ops_start,
            ops_end=request.ops_end,
            reference_period=reference_period,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            period=request.period,
            unit=request.unit,
            quantity=request.quantity,
            scope1_factor_tco2e_per_uom=scope1_factor,
            scope3_factor_tco2e_per_uom=scope3_factor,
            scope1_emissions_tco2e=round_result(scope1_emissions)
            if scope1_emissions
            else None,
            scope3_emissions_tco2e=round_result(scope3_emissions)
            if scope3_emissions
            else None,
            total_emissions_tco2e=round_result(total_emissions) if total_emissions else None,
        )

    async def _fetch_factor(
        self,
        db: AsyncSession,
        jurisdiction: str,
        emissions_category: str,
        emissions_sub_category: str,
        emissions_source: str,
        scope_field: str,
    ) -> Optional[float]:
        """
        Query v_grade34_detailed_level for Scope 1 or Scope 3 factor.
        scope_field: 'emission_factor_scope1' or 'emission_factor_scope3'
        """
        sql = f"""
            SELECT {scope_field}
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction" = :jurisdiction
              AND "Emissions Category" = :emissions_category
              AND "Emissions Sub-Category" = :emissions_sub_category
              AND "Emissions Source" = :emissions_source
            LIMIT 1
        """
        result = await db.execute(
            text(sql),
            {
                "jurisdiction": jurisdiction,
                "emissions_category": emissions_category,
                "emissions_sub_category": emissions_sub_category,
                "emissions_source": emissions_source,
            },
        )
        row = result.fetchone()

        if row is None:
            return None

        factor = row[0]
        if isinstance(factor, Decimal):
            return float(factor)
        return float(factor) if factor is not None else None


# Module-level singleton
calculator = DetailedMaintenanceCalculator()
