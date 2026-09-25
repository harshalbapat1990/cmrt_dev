# """
# services/detailed_level_calcs_operational_elec.py

# Service for Operational Energy (B6) and Water (B7) - Detailed Level -
# Operations (B6-7) Stage (Electricity ONLY) calculations.

# Excel source: tbl_detailed_level_calcs_operational_elec
# Sheet: MVP - Grade 1234
# Reference cells: $C$804 = Jurisdiction, $C$805 = Region/State

# Multipliers by emission source
# -------------------------------
#   Grid Electricity             → lb_mult = +1,  mb_mult = +1
#   Onsite Renewable Electricity → lb_mult = -1,  mb_mult = -1
#   Offsite Renewable Electricity→ lb_mult =  0,  mb_mult = -1

# Formulas (per row per year)
# ---------------------------
#   Location-Based Scope 2 (tCO2e) = lb_mult × Quantity(MWh) × scope2_LB(region, year)
#   Location-Based Scope 3 (tCO2e) = lb_mult × Quantity(MWh) × scope3_LB(region, year)
#   Market-Based Scope 2   (tCO2e) = mb_mult × Quantity(MWh) × (1 − RPP(jurisdiction, year))
#                                   × scope2_MB(jurisdiction, year)
#   Market-Based Scope 3   (tCO2e) = mb_mult × Quantity(MWh) × (1 − RPP(jurisdiction, year))
#                                   × scope3_MB(jurisdiction, year)
#   Location-Based Total   (tCO2e) = Scope2_LB + Scope3_LB
#   Market-Based Total     (tCO2e) = Scope2_MB + Scope3_MB

# Factor lookup: v_elec_decarb_scenarios (wide table: columns 2026…2100)
#   scope2_location — filtered by jurisdiction + region (region IS NOT NULL)
#   scope3_location — filtered by jurisdiction + region (region IS NOT NULL)
#   scope2_market   — filtered by jurisdiction only    (region IS NULL)
#   scope3_market   — filtered by jurisdiction only    (region IS NULL)
#   renewable_pct   — filtered by jurisdiction only    (region IS NULL)
# """

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EMISSION_SOURCES = frozenset({
    "Grid Electricity",
    "Onsite Renewable Electricity",
    "Offsite Renewable Electricity",
})

# (lb_mult, mb_mult) as per Excel IFS formulas
_MULTIPLIERS: dict[str, tuple[int, int]] = {
    "Grid Electricity":              ( 1,  1),
    "Onsite Renewable Electricity":  (-1, -1),
    "Offsite Renewable Electricity": ( 0, -1),
}

_LOCATION_TYPES = ("scope2_location", "scope3_location")
_MARKET_TYPES   = ("scope2_market", "scope3_market", "renewable_pct")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OperationalElecRequest(BaseModel):
    """
    Input for a single row of tbl_detailed_level_calcs_operational_elec.
    """
    jurisdiction: str = Field(
        ...,
        description=(
            "Jurisdiction name (e.g. 'Australia', 'New Zealand'). "
            "Cell $C$804 in Excel."
        ),
    )
    region: str = Field(
        ...,
        description=(
            "Grid region / state name for location-based lookups "
            "(e.g. 'New South Wales', 'National'). Cell $C$805 in Excel."
        ),
    )
    emission_source: str = Field(
        ...,
        description=(
            "One of: 'Grid Electricity', "
            "'Onsite Renewable Electricity', "
            "'Offsite Renewable Electricity'."
        ),
    )
    year: int = Field(
        ...,
        ge=2026,
        # le=2100,
        # description="Calendar year of the calculation row (2026–2100).",
        description="Calendar year of the calculation row.",
    )
    quantity_mwh: float = Field(
        ...,
        gt=0,
        description="Electricity quantity in MWh.",
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measure — echoed in response, not used in calculation.",
    )
    notes: Optional[str] = Field(
        None,
        description="Free-text notes — echoed in response, not used in calculation.",
    )
    dataset_revision_id: Optional[UUID] = Field(
        None,
        description=(
            "Dataset revision UUID to pin factors to a specific revision. "
            "If omitted, all active revisions for the jurisdiction/region are considered."
        ),
    )

    @field_validator("emission_source")
    @classmethod
    def validate_emission_source(cls, v: str) -> str:
        if v not in VALID_EMISSION_SOURCES:
            raise ValueError(
                f"emission_source must be one of: {sorted(VALID_EMISSION_SOURCES)}"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "region": "New South Wales",
                "emission_source": "Grid Electricity",
                "year": 2029,
                "quantity_mwh": 10.0,
                "unit": "MWh",
                "notes": None,
                "dataset_revision_id": None,
            }
        }
    }


class OperationalElecResponse(BaseModel):
    """
    Calculated emissions for one row of tbl_detailed_level_calcs_operational_elec.
    """
    # --- Echoed inputs ---
    jurisdiction: str
    region: str
    emission_source: str
    year: int
    quantity_mwh: float
    unit: Optional[str]
    notes: Optional[str]

    # --- Calculated outputs (tCO2e) ---
    location_based_emissions_tco2e: Optional[float] = Field(
        None,
        description="Location-Based Emissions (tCO2e) = Scope2_LB + Scope3_LB",
    )
    market_based_emissions_tco2e: Optional[float] = Field(
        None,
        description="Market-Based Emissions (tCO2e) = Scope2_MB + Scope3_MB",
    )
    scope2_location_based_tco2e: Optional[float] = Field(
        None,
        description="Location-Based Scope 2 Emissions (tCO2e)",
    )
    scope2_market_based_tco2e: Optional[float] = Field(
        None,
        description="Market-Based Scope 2 Emissions (tCO2e)",
    )
    scope3_location_based_tco2e: Optional[float] = Field(
        None,
        description="Location-Based Scope 3 Emissions (tCO2e)",
    )
    scope3_market_based_tco2e: Optional[float] = Field(
        None,
        description="Market-Based Scope 3 Emissions (tCO2e)",
    )

    # --- Raw factors (for transparency) ---
    scope2_location_factor: Optional[float] = Field(
        None,
        description="tCO2e/MWh — Scope 2 location-based EF for (region, year)",
    )
    scope2_market_factor: Optional[float] = Field(
        None,
        description="tCO2e/MWh — Scope 2 market-based EF for (jurisdiction, year)",
    )
    scope3_location_factor: Optional[float] = Field(
        None,
        description="tCO2e/MWh — Scope 3 location-based EF for (region, year)",
    )
    scope3_market_factor: Optional[float] = Field(
        None,
        description="tCO2e/MWh — Scope 3 market-based EF for (jurisdiction, year)",
    )
    renewable_pct_factor: Optional[float] = Field(
        None,
        description="RPP — renewable penetration proportion for (jurisdiction, year)",
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class OperationalElecCalculator:
    """
    Replicates Excel tbl_detailed_level_calcs_operational_elec formulas.

    Fetches all five factor types in one query from v_elec_decarb_scenarios
    (wide table with year columns "2026"…"2100"), selecting the column
    matching the requested year.
    """

    @staticmethod
    def _interpolate_factor_value(
        requested_year: int,
        values: list[tuple[int, float]],
    ) -> Optional[float]:
        """
        values must be sorted ascending by year.

        Behaviour:
        - exact match -> exact value
        - gap -> linear interpolation
        - after max year -> latest value
        - before min year -> earliest value
        """
        
        if not values:
            return None

        values = sorted(values, key=lambda x: x[0])

        for factor_year, factor_value in values:
            if factor_year == requested_year:
                return factor_value

        earliest_year, earliest_value = values[0]
        latest_year, latest_value = values[-1]

        if requested_year < earliest_year:
            return earliest_value

        if requested_year > latest_year:
            return latest_value

        lower_year: Optional[int] = None
        lower_value: Optional[float] = None
        upper_year: Optional[int] = None
        upper_value: Optional[float] = None

        for factor_year, factor_value in values:
            if factor_year < requested_year:
                lower_year = factor_year
                lower_value = factor_value
                continue

            if factor_year > requested_year:
                upper_year = factor_year
                upper_value = factor_value
                break

        if (
            lower_year is None
            or upper_year is None
            or lower_value is None
            or upper_value is None
        ):
            return None

        return lower_value + (
            (requested_year - lower_year)
            / (upper_year - lower_year)
        ) * (
            upper_value - lower_value
        )
    

    async def calculate(
        self,
        db: AsyncSession,
        request: OperationalElecRequest,
    ) -> OperationalElecResponse:

        factors = await self._fetch_factors(db, request)

        lb_mult, mb_mult = _MULTIPLIERS[request.emission_source]
        qty = request.quantity_mwh

        f_s2_lb = factors.get("scope2_location")
        f_s3_lb = factors.get("scope3_location")
        f_s2_mb = factors.get("scope2_market")
        f_s3_mb = factors.get("scope3_market")
        rpp     = factors.get("renewable_pct") or 0.0

        # Location-based: lb_mult × qty × factor
        s2_lb = (lb_mult * qty * f_s2_lb) if f_s2_lb is not None else None
        s3_lb = (lb_mult * qty * f_s3_lb) if f_s3_lb is not None else None

        # Market-based: mb_mult × qty × (1 − RPP) × factor
        s2_mb = (mb_mult * qty * (1.0 - rpp) * f_s2_mb) if f_s2_mb is not None else None
        s3_mb = (mb_mult * qty * (1.0 - rpp) * f_s3_mb) if f_s3_mb is not None else None

        lb_total = (s2_lb + s3_lb) if (s2_lb is not None and s3_lb is not None) else None
        mb_total = (s2_mb + s3_mb) if (s2_mb is not None and s3_mb is not None) else None

        return OperationalElecResponse(
            jurisdiction=request.jurisdiction,
            region=request.region,
            emission_source=request.emission_source,
            year=request.year,
            quantity_mwh=qty,
            unit=request.unit,
            notes=request.notes,
            location_based_emissions_tco2e=_round(lb_total),
            market_based_emissions_tco2e=_round(mb_total),
            scope2_location_based_tco2e=_round(s2_lb),
            scope2_market_based_tco2e=_round(s2_mb),
            scope3_location_based_tco2e=_round(s3_lb),
            scope3_market_based_tco2e=_round(s3_mb),
            scope2_location_factor=f_s2_lb,
            scope2_market_factor=f_s2_mb,
            scope3_location_factor=f_s3_lb,
            scope3_market_factor=f_s3_mb,
            renewable_pct_factor=factors.get("renewable_pct"),
        )
    
    
    async def _fetch_factors(
        self,
        db: AsyncSession,
        request: OperationalElecRequest,
    ) -> dict[str, float]:
        """
        Supports:

        - Exact year lookup
        - Linear interpolation between years
        - Carry-forward after latest available year
        - Carry-back before earliest available year
        """

        revision_clause = (
            "AND dataset_revision_id = CAST(:dataset_revision_id AS uuid)"
            if request.dataset_revision_id is not None
            else ""
        )

        year_columns = ", ".join(
            f'"{year}"'
            for year in range(2026, 2101)
        )

        sql = f"""
            SELECT
                factor_type_code,
                {year_columns}
            FROM v_elec_decarb_scenarios
            WHERE jurisdiction = :jurisdiction
              AND (
                    (
                        factor_type_code IN (
                            'scope2_location',
                            'scope3_location'
                        )
                        AND region = :region
                    )
                    OR
                    (
                        factor_type_code IN (
                            'scope2_market',
                            'scope3_market',
                            'renewable_pct'
                        )
                        AND region IS NULL
                    )
              )
              {revision_clause}
        """

        params: dict[str, object] = {
            "jurisdiction": request.jurisdiction,
            "region": request.region,
        }

        if request.dataset_revision_id is not None:
            params["dataset_revision_id"] = str(
                request.dataset_revision_id
            )

        result = await db.execute(text(sql), params)

        rows = result.fetchall()

        factors: dict[str, float] = {}

        for row in rows:
            yearly_values: list[tuple[int, float]] = []

            for yr in range(2026, 2101):
                value = getattr(row, str(yr), None)

                if value is not None:
                    yearly_values.append(
                        (
                            yr,
                            float(value),
                        )
                    )

            interpolated_value = self._interpolate_factor_value(
                requested_year=request.year,
                values=yearly_values,
            )

            if interpolated_value is not None:
                factors[row.factor_type_code] = interpolated_value

        return factors
    # async def _fetch_factors(
    #     self,
    #     db: AsyncSession,
    #     request: OperationalElecRequest,
    # ) -> dict[str, float]:
    #     """
    #     Queries v_elec_decarb_scenarios for the five factor types needed.

    #     The view is wide-format (one row per jurisdiction/region/factor_type,
    #     one column per year 2026–2100). A dynamic column reference is used to
    #     extract the requested year; the year is validated as int [2026,2100]
    #     so interpolating it into the SQL identifier is safe.

    #     Returns {factor_type_code: float_value}. Missing factor types are
    #     absent from the dict (caller maps them to None).
    #     """
    #     year = request.year  # validated int in [2026, 2100]

    #     # Dynamic column reference — safe: year is a validated integer constant
    #     year_col = f'"{year}"'

    #     revision_clause = (
    #         "AND dataset_revision_id = CAST(:dataset_revision_id AS uuid)"
    #         if request.dataset_revision_id is not None
    #         else ""
    #     )

    #     sql = f"""
    #         SELECT
    #             factor_type_code,
    #             {year_col}::double precision AS value
    #         FROM v_elec_decarb_scenarios
    #         WHERE jurisdiction = :jurisdiction
    #           AND (
    #             (
    #                 factor_type_code IN ('scope2_location', 'scope3_location')
    #                 AND region = :region
    #             )
    #             OR
    #             (
    #                 factor_type_code IN ('scope2_market', 'scope3_market', 'renewable_pct')
    #                 AND region IS NULL
    #             )
    #           )
    #           {revision_clause}
    #     """

    #     params: dict = {
    #         "jurisdiction": request.jurisdiction,
    #         "region": request.region,
    #     }
    #     if request.dataset_revision_id is not None:
    #         params["dataset_revision_id"] = str(request.dataset_revision_id)

    #     result = await db.execute(text(sql), params)
    #     return {
    #         row.factor_type_code: float(row.value)
    #         for row in result.fetchall()
    #         if row.value is not None
    #     }


_round = round_result


# Module-level singleton
calculator = OperationalElecCalculator()
