# """
# services/operational_component_level_calcs.py

# Service for Operational Energy (B6) - Component Level - Operations Stage calculations.

# Based on Excel formulas from 'MVP - Grade 1234' sheet (tbl_component_level_operational).

# Calculation flow
# ----------------
# 1. Lookup `annual_electricity_consumption_mwh` per unit from `operational_equipment` table
#    by matching `emissions_source` to `item`. Formula:
#        annual_mwh_per_unit = power_kw * hours_per_day * days_per_year / 1000

#    If the emissions source is not found in operational_equipment (e.g. Onsite/Offsite
#    Renewable where no equipment entry exists), `quantity` is treated directly as MWh/year.

# 2. Compute reference period:
#        reference_period = MIN(ops_end - ops_start, 50)
#        effective_end    = ops_start + reference_period

# 3. For each calendar year y in [ops_start, effective_end]:
#        consumption_y = annual_mwh * quantity   (if ops_start <= y <= effective_end)

# 4. Fetch all electric_decarb_factors for the jurisdiction/region across [ops_start, effective_end].

# 5. Sum per-year emissions using multipliers based on emission_source_type:
#        (lb_mult, mb_mult):
#            Grid Electricity            → (+1, +1)
#            Onsite Renewable Elec.      → (-1, -1)
#            Offsite Renewable Elec.     → ( 0, -1)

#        scope2_lb_y = lb_mult * consumption_y * scope2_location_factor(region, y)
#        scope3_lb_y = lb_mult * consumption_y * scope3_location_factor(region, y)

#        scope2_mb_y = mb_mult * consumption_y * (1 - RPP(jurisdiction, y))
#                               * scope2_market_factor(jurisdiction, y)
#        scope3_mb_y = mb_mult * consumption_y * (1 - RPP(jurisdiction, y))
#                               * scope3_market_factor(jurisdiction, y)

# 6. Sum across all active years:
#        scope2_lb_total  = SUM(scope2_lb_y)
#        scope2_mb_total  = SUM(scope2_mb_y)
#        scope3_lb_total  = SUM(scope3_lb_y)
#        scope3_mb_total  = SUM(scope3_mb_y)
#        location_based   = scope2_lb_total + scope3_lb_total
#        market_based     = scope2_mb_total + scope3_mb_total

# Factor type codes in electric_decarb_factors
# --------------------------------------------
#     scope2_location — matched by jurisdiction + region (has region_id)
#     scope3_location — matched by jurisdiction + region (has region_id)
#     scope2_market   — matched by jurisdiction only     (region_id IS NULL)
#     scope3_market   — matched by jurisdiction only     (region_id IS NULL)
#     renewable_pct   — RPP; matched by jurisdiction only (region_id IS NULL)
# """

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EMISSION_SOURCE_TYPES = frozenset({
    "Grid Electricity",
    "Onsite Renewable Electricity",
    "Offsite Renewable Electricity",
})

# (lb_mult, mb_mult)
_MULTIPLIERS: dict[str, tuple[int, int]] = {
    "Grid Electricity":              ( 1,  1),
    "Onsite Renewable Electricity":  (-1, -1),
    "Offsite Renewable Electricity": ( 0, -1),
}

_MIN_YEAR = 2026
_MAX_YEAR = 2100
_MAX_REFERENCE_PERIOD = 50


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OperationalComponentRequest(BaseModel):
    """
    Input for a single Component Level Operational Energy calculation row
    (one row of tbl_component_level_operational).
    """

    # Project-level context
    project_id: UUID = Field(
        ...,
        description="Project UUID (required). Region and dataset revision are resolved from project context via organization and project_dataset_revisions.",
    )
    jurisdiction: str = Field(
        ...,
        description="Jurisdiction name for market-based lookups (e.g. 'Australia')",
    )
    region: Optional[str] = Field(
        None,
        description="Deprecated. Region is automatically resolved from project organization. This field is ignored.",
    )
    ops_start: int = Field(
        ...,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations start year (C760)",
    )
    ops_end: int = Field(
        ...,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations end year (C761)",
    )

    # Row-level data
    emissions_category: Optional[str] = Field(
        None,
        description="Emissions category label (e.g. 'Operational Energy (B6)') — echoed in response",
    )
    emissions_sub_category: Optional[str] = Field(
        None,
        description="Emissions sub-category label (e.g. 'Electricity') — echoed in response",
    )
    emissions_source: str = Field(
        ...,
        description=(
            "Emissions source / equipment item name. "
            "Used as the lookup key in the operational_equipment table. "
            "If not found (e.g. for renewable sources), quantity is treated as MWh/year directly."
        ),
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of quantity (e.g. 'items', 'MWh') — echoed in response",
    )
    quantity: float = Field(
        ...,
        gt=0,
        description=(
            "Number of items (when emissions_source maps to an equipment entry) "
            "or annual electricity in MWh/year (when no equipment entry is found)."
        ),
    )
    emission_source_type: str = Field(
        "Grid Electricity",
        description=(
            "Electricity type for multiplier selection: "
            "'Grid Electricity', 'Onsite Renewable Electricity', or 'Offsite Renewable Electricity'"
        ),
    )

    @field_validator("emission_source_type")
    @classmethod
    def validate_emission_source_type(cls, v: str) -> str:
        if v not in VALID_EMISSION_SOURCE_TYPES:
            raise ValueError(
                f"emission_source_type must be one of: {sorted(VALID_EMISSION_SOURCE_TYPES)}"
            )
        return v

    @field_validator("ops_end")
    @classmethod
    def validate_ops_end(cls, v: int, info) -> int:
        ops_start = info.data.get("ops_start")
        if ops_start is not None and v <= ops_start:
            raise ValueError("ops_end must be greater than ops_start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "jurisdiction": "Australia",
                "region": None,
                "ops_start": 2029,
                "ops_end": 2100,
                "emissions_category": "Operational Energy (B6)",
                "emissions_sub_category": "Electricity",
                "emissions_source": "Major arterial LED lighting (Category V1-V2)",
                "unit": "items",
                "quantity": 5,
                "emission_source_type": "Grid Electricity",
            }
        }
    }


class OperationalComponentResponse(BaseModel):
    """Calculated emissions for a single Component Level Operational row (tCO2e)."""

    # Echo inputs
    jurisdiction: str
    region: str
    ops_start: int
    ops_end: int
    reference_period: int = Field(
        ..., description="MIN(ops_end - ops_start, 50) — effective number of operational years"
    )
    effective_end: int = Field(
        ..., description="ops_start + reference_period — last calendar year included in sum (enforces 50-year reference period cap)"
    )
    emissions_category: Optional[str]
    emissions_sub_category: Optional[str]
    emissions_source: str
    emission_source_type: str
    unit: Optional[str]
    quantity: float

    # Derived consumption
    annual_mwh_per_unit: Optional[float] = Field(
        None,
        description=(
            "Annual electricity consumption per unit (MWh/year) looked up from "
            "operational_equipment. Null when quantity is treated as MWh directly."
        ),
    )
    annual_consumption_mwh: float = Field(
        ...,
        description="Total annual consumption = annual_mwh_per_unit * quantity (or quantity when no lookup)",
    )

    # Output columns matching tbl_component_level_operational
    location_based_total_tco2e: Optional[float] = Field(
        None, description="Location-Based Emissions (tCO2e) = Scope2_LB + Scope3_LB summed over ref period"
    )
    market_based_total_tco2e: Optional[float] = Field(
        None, description="Market-Based Emissions (tCO2e) = Scope2_MB + Scope3_MB summed over ref period"
    )
    scope2_location_based_tco2e: Optional[float] = Field(
        None, description="Location-Based Scope 2 Emissions (tCO2e)"
    )
    scope2_market_based_tco2e: Optional[float] = Field(
        None, description="Market-Based Scope 2 Emissions (tCO2e)"
    )
    scope3_location_based_tco2e: Optional[float] = Field(
        None, description="Location-Based Scope 3 Emissions (tCO2e)"
    )
    scope3_market_based_tco2e: Optional[float] = Field(
        None, description="Market-Based Scope 3 Emissions (tCO2e)"
    )

    # ------------------------------------------------------------------
    # Intermediate debug tables (year → value, spanning 2026-2100)
    # Matches Excel tbl_ops_electricity_* structure — no emission-type
    # multiplier applied; outside [ops_start, effective_end] values are 0.
    # ------------------------------------------------------------------
    # COMMENTED OUT: Supporting tables not required for production response
    # tbl_ops_electricity_consumption: Optional[dict[int, float]] = Field(
    #     None,
    #     description="Annual electricity consumption (MWh) per year [Excel: tbl_ops_electricity_consumption]",
    # )
    # tbl_ops_electricity_s2_emissions_LB: Optional[dict[int, float]] = Field(
    #     None,
    #     description="Scope 2 LB emissions per year (tCO2e) = consumption × scope2_location_factor",
    # )
    # tbl_ops_electricity_s2_emissions_MB: Optional[dict[int, float]] = Field(
    #     None,
    #     description="Scope 2 MB emissions per year (tCO2e) = scope2_market_factor × consumption × (1-RPP)",
    # )
    # tbl_ops_electricity_s3_emissions_LB: Optional[dict[int, float]] = Field(
    #     None,
    #     description="Scope 3 LB emissions per year (tCO2e) = consumption × scope3_location_factor",
    # )
    # tbl_ops_electricity_s3_emissions_MB: Optional[dict[int, float]] = Field(
    #     None,
    #     description="Scope 3 MB emissions per year (tCO2e) = scope3_market_factor × consumption × (1-RPP)",
    # )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class OperationalComponentCalculator:
    """
    Computes location-based and market-based operational electricity emissions
    for one tbl_component_level_operational row, summed across the reference period.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: OperationalComponentRequest,
    ) -> OperationalComponentResponse:

        # 0. Resolve region and dataset_revision_id from project_id
        if not request.project_id:
            raise ValueError(
                "project_id is required. It is used to resolve region and dataset revision from project context."
            )
        
        region = await ProjectContextHelper.fetch_project_region(db, request.project_id)
        dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(
            db, request.project_id
        )
        
        if not region:
            raise ValueError(
                f"Could not resolve region for project {request.project_id}."
            )
        
        if not dataset_revision_id:
            raise ValueError(
                f"Could not resolve dataset_revision_id for project {request.project_id}. "
                f"Ensure either ProjectDatasetRevision assignment exists or DEFAULT dataset revision is available."
            )

        # 1. Compute reference period and effective year range.
        # reference_period is MIN(ops_end - ops_start, 50) — caps operations at 50 years.
        # effective_end is ops_start + reference_period — the last calendar year included.
        reference_period = min(request.ops_end - request.ops_start, _MAX_REFERENCE_PERIOD)
        effective_end = request.ops_start + reference_period

        # 2. Lookup annual electricity consumption from operational_equipment
        annual_mwh_per_unit, annual_consumption_mwh = await self._fetch_annual_consumption(
            db=db,
            emissions_source=request.emissions_source,
            quantity=request.quantity,
            dataset_revision_id=dataset_revision_id,
        )

        # 3. Fetch all factor values for the active year range in one query
        factors_by_year = await self._fetch_factors_by_year(
            db=db,
            jurisdiction=request.jurisdiction,
            region=region,
            ops_start=request.ops_start,
            effective_end=effective_end,
            dataset_revision_id=dataset_revision_id,
        )

        # 4. Sum emissions across all active years
        lb_mult, mb_mult = _MULTIPLIERS[request.emission_source_type]

        sum_s2_lb = 0.0
        sum_s3_lb = 0.0
        sum_s2_mb = 0.0
        sum_s3_mb = 0.0

        any_lb_data = False
        any_mb_data = False

        # Intermediate tables — initialise all years 2026-2100 to zero.
        # Active years (ops_start..effective_end) are filled inside the loop.
        # COMMENTED OUT: Supporting tables not required for production response
        # _tbl_consumption: dict[int, float] = {y: 0.0 for y in range(_MIN_YEAR, _MAX_YEAR + 1)}
        # _tbl_s2_lb: dict[int, float] = {y: 0.0 for y in range(_MIN_YEAR, _MAX_YEAR + 1)}
        # _tbl_s2_mb: dict[int, float] = {y: 0.0 for y in range(_MIN_YEAR, _MAX_YEAR + 1)}
        # _tbl_s3_lb: dict[int, float] = {y: 0.0 for y in range(_MIN_YEAR, _MAX_YEAR + 1)}
        # _tbl_s3_mb: dict[int, float] = {y: 0.0 for y in range(_MIN_YEAR, _MAX_YEAR + 1)}

        for year in range(request.ops_start, effective_end + 1):
            f = factors_by_year.get(year, {})

            s2_loc = f.get("scope2_location")
            s3_loc = f.get("scope3_location")
            s2_mkt = f.get("scope2_market")
            s3_mkt = f.get("scope3_market")
            rpp = f.get("renewable_pct", 0.0)

            if s2_loc is not None:
                sum_s2_lb += s2_loc
                any_lb_data = True
            if s3_loc is not None:
                sum_s3_lb += s3_loc
                any_lb_data = True

            if s2_mkt is not None:
                sum_s2_mb += s2_mkt * (1.0 - rpp)
                any_mb_data = True
            if s3_mkt is not None:
                sum_s3_mb += s3_mkt * (1.0 - rpp)
                any_mb_data = True

            # Populate intermediate tables (no emission-type multiplier,
            # matching Excel tbl_ops_electricity_* formula structure)
            # COMMENTED OUT: Supporting tables not required for production response
            # _tbl_consumption[year] = annual_consumption_mwh
            # _tbl_s2_lb[year] = annual_consumption_mwh * (s2_loc or 0.0)
            # _tbl_s2_mb[year] = (s2_mkt or 0.0) * annual_consumption_mwh * (1.0 - rpp)
            # _tbl_s3_lb[year] = annual_consumption_mwh * (s3_loc or 0.0)
            # _tbl_s3_mb[year] = (s3_mkt or 0.0) * annual_consumption_mwh * (1.0 - rpp)

        # 5. Apply multiplier × annual consumption
        s2_lb = (lb_mult * annual_consumption_mwh * sum_s2_lb) if any_lb_data else None
        s3_lb = (lb_mult * annual_consumption_mwh * sum_s3_lb) if any_lb_data else None
        s2_mb = (mb_mult * annual_consumption_mwh * sum_s2_mb) if any_mb_data else None
        s3_mb = (mb_mult * annual_consumption_mwh * sum_s3_mb) if any_mb_data else None

        lb_total = (s2_lb + s3_lb) if (s2_lb is not None and s3_lb is not None) else None
        mb_total = (s2_mb + s3_mb) if (s2_mb is not None and s3_mb is not None) else None

        return OperationalComponentResponse(
            jurisdiction=request.jurisdiction,
            region=region,
            ops_start=request.ops_start,
            ops_end=request.ops_end,
            reference_period=reference_period,
            effective_end=effective_end,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            emission_source_type=request.emission_source_type,
            unit=request.unit,
            quantity=request.quantity,
            annual_mwh_per_unit=annual_mwh_per_unit,
            annual_consumption_mwh=annual_consumption_mwh,
            location_based_total_tco2e=_round(lb_total),
            market_based_total_tco2e=_round(mb_total),
            scope2_location_based_tco2e=_round(s2_lb),
            scope2_market_based_tco2e=_round(s2_mb),
            scope3_location_based_tco2e=_round(s3_lb),
            scope3_market_based_tco2e=_round(s3_mb),
            # COMMENTED OUT: Supporting tables not required for production response
            # tbl_ops_electricity_consumption=_tbl_consumption,
            # tbl_ops_electricity_s2_emissions_LB=_tbl_s2_lb,
            # tbl_ops_electricity_s2_emissions_MB=_tbl_s2_mb,
            # tbl_ops_electricity_s3_emissions_LB=_tbl_s3_lb,
            # tbl_ops_electricity_s3_emissions_MB=_tbl_s3_mb,
        )

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _fetch_annual_consumption(
        self,
        db: AsyncSession,
        emissions_source: str,
        quantity: float,
        dataset_revision_id: Optional[UUID],
    ) -> tuple[Optional[float], float]:
        """
        Lookup annual_mwh_per_unit from operational_equipment.

        Filters by:
          - item = emissions_source  (matches Excel XLOOKUP by item name only)

        The Excel formula does: XLOOKUP(emissions_source, item_range, annual_mwh_range)
        — no group filtering — so group_name is intentionally not used here.

        IMPORTANT: Equipment lookup uses a fallback strategy:
          1. First try to find equipment in the specific dataset revision
          2. If not found, fall back to global equipment (dataset_revision_id IS NULL)
          3. If still no match, treat quantity as MWh/year directly

        Returns (annual_mwh_per_unit, annual_consumption_mwh).

        When no matching equipment row is found (e.g. renewable energy sources),
        annual_mwh_per_unit is None and annual_consumption_mwh = quantity
        (treating quantity as MWh/year directly).
        """
        # Build query that prefers specific revision but falls back to global equipment
        if dataset_revision_id:
            sql = """
                SELECT
                    (power_kw * hours_per_day * days_per_year / 1000.0)::double precision
                        AS annual_mwh_per_unit
                FROM operational_equipment
                WHERE
                    item = :item
                    AND is_active = TRUE
                    AND (
                        dataset_revision_id = CAST(:dataset_revision_id AS uuid)
                        OR dataset_revision_id IS NULL
                    )
                ORDER BY
                    (dataset_revision_id = CAST(:dataset_revision_id AS uuid)) DESC,
                    dataset_revision_id DESC NULLS LAST
                LIMIT 1
            """
            params: dict = {"item": emissions_source, "dataset_revision_id": str(dataset_revision_id)}
        else:
            sql = """
                SELECT
                    (power_kw * hours_per_day * days_per_year / 1000.0)::double precision
                        AS annual_mwh_per_unit
                FROM operational_equipment
                WHERE
                    item = :item
                    AND is_active = TRUE
                    AND dataset_revision_id IS NULL
                ORDER BY
                    dataset_revision_id DESC NULLS LAST
                LIMIT 1
            """
            params: dict = {"item": emissions_source}
        
        result = await db.execute(text(sql), params)
        row = result.fetchone()

        if row is None or row.annual_mwh_per_unit is None:
            # No equipment match — treat quantity as MWh/year directly
            return None, quantity

        annual_mwh_per_unit = float(row.annual_mwh_per_unit)
        return annual_mwh_per_unit, annual_mwh_per_unit * quantity

    async def _fetch_factors_by_year(
        self,
        db: AsyncSession,
        jurisdiction: str,
        region: str,
        ops_start: int,
        effective_end: int,
        dataset_revision_id: Optional[UUID],
    ) -> dict[int, dict[str, float]]:
        """
        Fetches electric_decarb_factors for all years in [ops_start, effective_end].

        Returns {year: {factor_type_code: value}}.
        """
        revision_clause = (
            "AND edf.dataset_revision_id = CAST(:dataset_revision_id AS uuid)"
            if dataset_revision_id
            else ""
        )
        sql = f"""
            SELECT DISTINCT ON (edf.year, edf.factor_type_code)
                edf.year,
                edf.factor_type_code,
                edf.value::double precision AS value
            FROM electric_decarb_factors edf
            JOIN jurisdictions j ON j.id = edf.jurisdiction_id
            LEFT JOIN grid_regions gr ON gr.id = edf.region_id
            WHERE
                edf.year >= :ops_start
                AND edf.year <= :effective_end
                AND j.name = :jurisdiction
                {revision_clause}
                AND (
                    (
                        edf.factor_type_code IN ('scope2_location', 'scope3_location')
                        AND gr.name = :region
                    )
                    OR
                    (
                        edf.factor_type_code IN ('scope2_market', 'scope3_market', 'renewable_pct')
                        AND edf.region_id IS NULL
                    )
                )
            ORDER BY edf.year, edf.factor_type_code, edf.dataset_revision_id DESC NULLS LAST
        """
        params: dict = {
            "ops_start": ops_start,
            "effective_end": effective_end,
            "jurisdiction": jurisdiction,
            "region": region,
        }

        if dataset_revision_id is not None:
            params["dataset_revision_id"] = str(dataset_revision_id)

        result = await db.execute(text(sql), params)

        factors_by_year: dict[int, dict[str, float]] = {}
        for row in result.fetchall():
            if row.value is not None:
                factors_by_year.setdefault(row.year, {})[row.factor_type_code] = float(row.value)

        return factors_by_year


_round = round_result


# Module-level singleton
calculator = OperationalComponentCalculator()
