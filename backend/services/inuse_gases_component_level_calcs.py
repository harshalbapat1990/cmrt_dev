# """
# services/inuse_gases_component_level_calcs.py

# Service for Operations and Maintenance - Use (B1) - Component Level - In Use (B1) Stage
# calculations (fugitive gases — refrigerants, insulants, etc.).

# Excel source: tbl_inuse_gases_component_level
# Sheet: MVP - Grade 1234

# Calculation flow
# ----------------
# 1. Compute reference period:
#        reference_period = MIN(ops_end - ops_start, 50)

# 2. Lookup Annual Leakage Rate (%) from fugitives table
#    by matching (jurisdiction, equipment_type).

# 3. Lookup Scope 1 Emissions Factor (tCO2e/kg) from v_grade34_detailed_level view
#    by matching (jurisdiction, gas).

# 4. Calculate Scope 1 emissions over the reference period:
#        Scope1_Emissions (tCO2e) =
#            Annual_Leakage_Rate(%) × Charge(kg) / 1000
#            × Scope1_Emissions_Factor(tCO2e/kg)
#            × Reference_Period (years)

# 5. Total Emissions (Scope 1 only):
#        Emissions (tCO2e) = Scope1_Emissions

# Factor columns in v_grade34_detailed_level:
#     emission_factor_scope1 — "Scope 1 Emissions Factor (tCO2e/kg or per unit)"
# """

from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result


# Constants
_MAX_YEAR = 2100
_MIN_YEAR = 2026
_MAX_REFERENCE_PERIOD = 50


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class InUseGasesRequest(BaseModel):
    """
    Input for a single row of tbl_inuse_gases_component_level.
    """
    # Project-level context
    jurisdiction: str = Field(
        ...,
        description="Jurisdiction name for lookups (e.g. 'Australia')",
    )
    ops_start: int = Field(
        ...,
        description="Operations start year (e.g. 2029)",
    )
    ops_end: int = Field(
        ...,
        description="Operations end year (e.g. 2100)",
    )

    # Row-level data
    application_type: str = Field(
        ...,
        description="Equipment type for leakage rate lookup (e.g. 'Commercial refrigeration')",
    )
    gas_type: Optional[str] = Field(
        None,
        description="Gas type label / Emissions Sub-Category (e.g. 'Hydrofluorocarbons (HFCs)')",
    )
    gas: str = Field(
        ...,
        description="Gas name / Emissions Source for scope1 factor lookup (e.g. 'HFC-23')",
    )
    charge_kg: float = Field(
        ...,
        gt=0,
        description="Charge in kg (initial refrigerant/insulation charge)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "ops_start": 2029,
                "ops_end": 2100,
                "application_type": "Commercial refrigeration",
                "gas_type": "Hydrofluorocarbons (HFCs)",
                "gas": "HFC-134a",
                "charge_kg": 45.0,
            }
        }
    }


class InUseGasesResponse(BaseModel):
    """Calculated Scope 1 emissions for one row of the In-Use gases table (tCO2e)."""

    # Echo inputs
    jurisdiction: str
    ops_start: int
    ops_end: int
    reference_period: int = Field(
        ..., description="MIN(ops_end - ops_start, 50) — reference period in years"
    )
    application_type: str
    gas_type: Optional[str]
    gas: str
    charge_kg: float
    emissions_category: str

    # Factors retrieved from lookups (for transparency)
    annual_leakage_rate_percent: Optional[float] = Field(
        None,
        description="Annual Leakage Rate (%) from fugitive_equipment table",
    )
    scope1_emissions_factor_tco2e_per_kg: Optional[float] = Field(
        None,
        description="Scope 1 Emissions Factor (tCO2e/kg) from v_grade34_detailed_level",
    )

    # Calculated outputs (tCO2e)
    scope1_emissions_tco2e: Optional[float] = Field(
        None,
        description="Scope 1 Emissions = Annual Leakage Rate(%) × Charge(kg) / 1000 × Factor × Reference Period",
    )
    total_emissions_tco2e: Optional[float] = Field(
        None,
        description="Total Emissions = Scope 1 (only scope in B1)",
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class InUseGasesCalculator:
    """
    Computes Scope 1 (fugitive) in-use gas emissions for one row.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: InUseGasesRequest,
    ) -> InUseGasesResponse:
        """
        Perform In-Use Gases (B1) calculation.

        Steps:
          1. Compute reference period = MIN(ops_end - ops_start, 50)
          2. Lookup annual leakage rate by (jurisdiction, application_type)
          3. Lookup scope1 factor by (jurisdiction, gas)
          4. Calculate emissions = leakage_rate(%) × charge(kg) / 1000 × factor × reference_period
        """

        # 1. Compute reference period
        reference_period = min(request.ops_end - request.ops_start, _MAX_REFERENCE_PERIOD)

        # 2. Lookup annual leakage rate
        annual_leakage_rate = await self._fetch_leakage_rate(
            db=db,
            jurisdiction=request.jurisdiction,
            application_type=request.application_type,
        )

        # 3. Lookup scope1 emissions factor
        scope1_factor = await self._fetch_scope1_factor(
            db=db,
            jurisdiction=request.jurisdiction,
            emissions_category="Gases",
            emissions_sub_category=request.gas_type,
            emissions_source=request.gas,
        )

        # 4. Calculate emissions
        scope1_emissions = None
        if annual_leakage_rate is not None and scope1_factor is not None:
            # Formula: leakage_rate(%) × charge(kg) / 1000 × factor(tCO2e/kg) × years
            scope1_emissions = (
                (annual_leakage_rate / 100.0)  # Convert percentage to decimal
                * request.charge_kg
                / 1000.0
                * scope1_factor
                * reference_period
            )

        total_emissions = scope1_emissions  # B1 only has Scope 1

        return InUseGasesResponse(
            jurisdiction=request.jurisdiction,
            ops_start=request.ops_start,
            ops_end=request.ops_end,
            reference_period=reference_period,
            application_type=request.application_type,
            gas_type=request.gas_type,
            gas=request.gas,
            charge_kg=request.charge_kg,
            emissions_category="Gases",
            annual_leakage_rate_percent=annual_leakage_rate,
            scope1_emissions_factor_tco2e_per_kg=scope1_factor,
            scope1_emissions_tco2e=round_result(scope1_emissions) if scope1_emissions else None,
            total_emissions_tco2e=round_result(total_emissions) if total_emissions else None,
        )

    async def _fetch_leakage_rate(
        self,
        db: AsyncSession,
        jurisdiction: str,
        application_type: str,
    ) -> Optional[float]:
        """
        Query fugitives table for the annual leakage rate.
        Matches: jurisdiction × equipment_type (application_type).
        """
        sql = """
            SELECT default_annual_leakage_rate
            FROM fugitives f
            JOIN jurisdictions j ON j.id = f.jurisdiction_id
            WHERE j.name = :jurisdiction
              AND f.equipment_type = :equipment_type
            LIMIT 1
        """
        result = await db.execute(
            text(sql),
            {
                "jurisdiction": jurisdiction,
                "equipment_type": application_type,
            },
        )
        row = result.fetchone()

        if row is None:
            return None

        rate = row.default_annual_leakage_rate
        if isinstance(rate, Decimal):
            return float(rate)
        return float(rate) if rate is not None else None

    async def _fetch_scope1_factor(
        self,
        db: AsyncSession,
        jurisdiction: str,
        emissions_category: str,
        emissions_sub_category: Optional[str],
        emissions_source: str,
    ) -> Optional[float]:
        """
        Query v_grade34_detailed_level for the Scope 1 emissions factor.
        Matches: jurisdiction × emissions_category × emissions_sub_category × emissions_source.
        """
        sub_cat_clause = (
            'AND "Emissions Sub-Category" = :emissions_sub_category'
            if emissions_sub_category is not None
            else ""
        )
        sql = f"""
            SELECT emission_factor_scope1
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction" = :jurisdiction
              AND "Emissions Category" = :emissions_category
              {sub_cat_clause}
              AND "Emissions Source" = :emissions_source
            LIMIT 1
        """
        params: dict = {
            "jurisdiction": jurisdiction,
            "emissions_category": emissions_category,
            "emissions_source": emissions_source,
        }
        if emissions_sub_category is not None:
            params["emissions_sub_category"] = emissions_sub_category
        result = await db.execute(text(sql), params)
        row = result.fetchone()

        if row is None:
            return None

        factor = row.emission_factor_scope1
        if isinstance(factor, Decimal):
            return float(factor)
        return float(factor) if factor is not None else None


# Module-level singleton
calculator = InUseGasesCalculator()
