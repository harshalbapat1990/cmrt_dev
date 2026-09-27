
# """
# services/electricity_detailed_calculations.py

# Service for Detailed Level - Electricity emissions calculations.

# Based on Excel formulas from 'Austroads CMRT Proposed Datasets_DRAFT_v1.01_05152026.xlsx'
# sheet 'Detailed Level - Electricity' (updated 2026-05-15).

# Location-Based multipliers by emission source (IFS formula)
# ------------------------------------------------------------
#   Grid Electricity               → lb_mult = +1
#   Onsite Renewable Electricity   → lb_mult =  0   (no LB emissions credited)
#   Offsite Renewable Electricity  → lb_mult = +1

# Market-Based multipliers by emission source (IFS formula)
# ---------------------------------------------------------
#   Grid Electricity               → mb_mult = +1
#   Onsite Renewable Electricity   → mb_mult =  0   (no MB emissions credited)
#   Offsite Renewable Electricity  → mb_mult =  0   (no MB emissions credited)

# Formulas
# --------
#   scope2_lb    = lb_mult × qty × scope2_location_factor(region, year)
#   scope3_lb    = lb_mult × qty × scope3_location_factor(region, year)

#   For Grid Electricity (mb_mult = 1):
#     net_mb_qty   = qty - sum_grid_and_offsite_mwh_for_year × RPP(jurisdiction, year)
#     scope2_mb    = net_mb_qty × scope2_market_factor(jurisdiction, year)
#     scope3_mb    = net_mb_qty × scope3_market_factor(jurisdiction, year)
#   For Onsite / Offsite Renewable (mb_mult = 0):
#     scope2_mb    = 0
#     scope3_mb    = 0

#   location_based_total = scope2_lb + scope3_lb
#   market_based_total   = scope2_mb + scope3_mb

# SUMIFS cross-row context (market-based Grid Electricity only)
# --------------------------------------------------------------
#   The Excel SUMIFS([Quantity (MWh)],[Emission Source],
#   {"Grid Electricity","Offsite Renewable Electricity"},[Year],[@Year])
#   is resolved automatically from the activity_data table.
#   The caller must supply project_stage_instance_id + project_option_id so
#   the backend can query all saved electricity rows for the same year across
#   ui_table_key values: 'electricity', 'opEnergyElectricity', 'electricity-mitigation'.
#   Falls back to quantity_mwh when either key is absent.

# Factor type codes in electric_decarb_factors
# ---------------------------------------------
#   scope2_location  — matched by jurisdiction + region  (has region_id)
#   scope3_location  — matched by jurisdiction + region  (has region_id)
#   scope2_market    — matched by jurisdiction only       (region_id IS NULL)
#   scope3_market    — matched by jurisdiction only       (region_id IS NULL)
#   renewable_pct    — RPP; matched by jurisdiction only  (region_id IS NULL)
# """

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EMISSION_SOURCES = frozenset({
    "Grid Electricity",
    "Onsite Renewable Electricity",
    "Offsite Renewable Electricity",
})

# Location-based IFS multipliers
_LB_MULTIPLIERS: dict[str, int] = {
    "Grid Electricity":              1,
    "Onsite Renewable Electricity":  0,
    "Offsite Renewable Electricity": 1,
}

# Market-based IFS multipliers
_MB_MULTIPLIERS: dict[str, int] = {
    "Grid Electricity":              1,
    "Onsite Renewable Electricity":  0,
    "Offsite Renewable Electricity": 0,
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ElectricityDetailedRequest(BaseModel):
    """
    Input for a single Detailed Level Electricity calculation row.

    Either `project_id` OR both `jurisdiction` + `region` must be provided.
    When `project_id` is supplied the backend resolves jurisdiction and region
    from the project's postcode (same logic as the grid-context endpoint).
    """
    # --- Project context (preferred: resolves jurisdiction + region automatically) ---
    project_id: Optional[UUID] = Field(
        None,
        description=(
            "Project UUID. When provided, jurisdiction and region are resolved "
            "from the project's postcode. Takes precedence over explicit fields."
        ),
    )
    # --- Explicit context (required when project_id is not supplied) ---
    jurisdiction: Optional[str] = Field(
        None,
        description="Jurisdiction name (e.g. 'Australia', 'New Zealand'). Required if project_id is absent."
    )
    region: Optional[str] = Field(
        None,
        description="Grid region name for location-based lookups (e.g. 'New South Wales'). Required if project_id is absent."
    )
    # --- Row data ---
    emission_source: str = Field(
        ...,
        description=(
            "One of: 'Grid Electricity', "
            "'Onsite Renewable Electricity', "
            "'Offsite Renewable Electricity'"
        ),
    )
    year: int = Field(
        ..., 
        ge=2026, 
        # le=2100, 
        # description="Year of activity (2026–2100)"
        description="Year of activity"
    )
    quantity: float = Field(..., gt=0, description="Electricity quantity in the specified unit")
    unit: str = Field(
        default="MWh",
        description="Unit of quantity: 'kWh', 'MWh', or 'GWh'"
    )
    # --- Construction window (from construction_start_date / construction_end_date) ---
    construction_start_year: Optional[int] = Field(
        None,
        ge=2026,
        # le=2100,
        description=(
            "Start year of the construction period (from construction_start_date). "
            "When both construction years are provided, 'year' is validated to fall within this window."
        ),
    )
    construction_end_year: Optional[int] = Field(
        None,
        ge=2026,
        # le=2100,
        description=(
            "End year of the construction period (from construction_end_date). "
            "When both construction years are provided, 'year' is validated to fall within this window."
        ),
    )
    # --- Operations window (from commencement_of_operations + operational_life_years) ---
    ops_start_year: Optional[int] = Field(
        None,
        ge=2026,
        # le=2100,
        description=(
            "Start year of the operations period (from commencement_of_operations). "
            "When both ops years are provided, 'year' is validated to fall within this window."
        ),
    )
    ops_end_year: Optional[int] = Field(
        None,
        ge=2026,
        # le=2100,
        description=(
            "End year of the operations period (commencement_of_operations + operational_life_years). "
            "When both ops years are provided, 'year' is validated to fall within this window."
        ),
    )
    # --- Cross-row context (resolved from activity_data for market-based Grid Electricity) ---
    project_stage_instance_id: Optional[UUID] = Field(
        None,
        description=(
            "Project stage instance UUID. Together with project_option_id, used to query "
            "activity_data for the SUMIFS total of Grid + Offsite Renewable MWh for the same year. "
            "Required for accurate market-based emissions on Grid Electricity rows when "
            "multiple electricity rows exist across 'electricity', 'opEnergyElectricity', "
            "and 'electricity-mitigation' table keys."
        ),
    )
    project_option_id: Optional[UUID] = Field(
        None,
        description=(
            "Project option UUID. Used alongside project_stage_instance_id to scope the "
            "activity_data SUMIFS query to the correct option."
        ),
    )
    dataset_revision_id: Optional[UUID] = Field(
        None,
        description=(
            "Dataset revision UUID. "
            "If omitted, all revisions for the jurisdiction/region are considered."
        ),
    )
    ui_table_key: str = Field(
        ...,
        description=(
            "table section key for the row: 'electricity', 'opEnergyElectricity', or 'electricity-mitigation'. "
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

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        valid_units = {"kWh", "MWh", "GWh"}
        if v not in valid_units:
            raise ValueError(
                f"unit must be one of: {sorted(valid_units)}"
            )
        return v

    @field_validator("ui_table_key")
    @classmethod
    def validate_ui_table_key(cls, v: str) -> str:
        valid_keys = {"electricity", "opEnergyElectricity", "electricity-mitigation"}
        if v not in valid_keys:
            raise ValueError(
                f"ui_table_key must be one of: {sorted(valid_keys)}"
            )
        return v
    def model_post_init(self, __context: object) -> None:
        # Require either project_id or explicit jurisdiction + region
        if self.project_id is None:
            if not self.jurisdiction or not self.region:
                raise ValueError(
                    "Either 'project_id' must be provided, or both "
                    "'jurisdiction' and 'region' must be supplied."
                )
        # Default end years to 2100 when only the start year is supplied
        if self.construction_start_year is not None and self.construction_end_year is None:
            # object.__setattr__(self, "construction_end_year", 2100)
            object.__setattr__(self, "construction_end_year", 9999)
        if self.ops_start_year is not None and self.ops_end_year is None:
            # object.__setattr__(self, "ops_end_year", 2100)
            object.__setattr__(self, "ops_end_year", 9999)
        # Validate year against construction window (skip when both null — resolved later from project)
        if self.construction_start_year is not None and self.construction_end_year is not None:
            if not (self.construction_start_year <= self.year <= self.construction_end_year):
                raise ValueError(
                    f"year {self.year} is outside the construction window "
                    f"{self.construction_start_year}–{self.construction_end_year}."
                )
        # Validate year against operations window (skip when both null — resolved later from project)
        if self.ops_start_year is not None and self.ops_end_year is not None:
            if not (self.ops_start_year <= self.year <= self.ops_end_year):
                raise ValueError(
                    f"year {self.year} is outside the operations window "
                    f"{self.ops_start_year}–{self.ops_end_year}."
                )

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "project_stage_instance_id": "9b3dd166-03ac-4c4a-82d8-1d6794860fd8",
                "project_option_id": "a9f80066-f49e-4664-8397-225f44fc4ce3",
                "emission_source": "Grid Electricity",
                "year": 2029,
                "quantity": 464,
                "unit": "MWh",
                "construction_start_year": 2026,
                "construction_end_year": 2030,
                "ops_start_year": 2031,
                "ops_end_year": 2081,
                "ui_table_key": "electricity",
            }
        }
    }


class ElectricityDetailedResponse(BaseModel):
    """Calculated emissions for a single Detailed Level Electricity row."""
    # Echo inputs
    project_id: Optional[UUID] = None
    jurisdiction: str
    region: str
    emission_source: str
    year: int
    quantity_mwh: float
    construction_start_year: Optional[int] = None
    construction_end_year: Optional[int] = None
    ops_start_year: Optional[int] = None
    ops_end_year: Optional[int] = None

    # Calculated outputs (tCO2e) — null when the required factor is missing for the year
    location_based_total_tco2e: Optional[float] = Field(
        None, description="Location-Based Emissions (tCO2e) = Scope2_LB + Scope3_LB"
    )
    market_based_total_tco2e: Optional[float] = Field(
        None, description="Market-Based Emissions (tCO2e) = Scope2_MB + Scope3_MB"
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

    # Raw factors (exposed for transparency / debugging)
    scope2_location_factor: Optional[float] = Field(
        None, description="tCO2e/MWh — Scope 2 location-based EF for the region/year"
    )
    scope2_market_factor: Optional[float] = Field(
        None, description="tCO2e/MWh — Scope 2 market-based EF for the jurisdiction/year"
    )
    scope3_location_factor: Optional[float] = Field(
        None, description="tCO2e/MWh — Scope 3 location-based EF for the region/year"
    )
    scope3_market_factor: Optional[float] = Field(
        None, description="tCO2e/MWh — Scope 3 market-based EF for the jurisdiction/year"
    )
    renewable_pct_factor: Optional[float] = Field(
        None, description="RPP — renewable penetration proportion for the jurisdiction/year"
    )


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class ElectricityDetailedCalculator:
    """
    Computes location-based and market-based electricity emissions for one row.

    Fetches all 5 factor types in a single DB query from electric_decarb_factors:
      - scope2_location, scope3_location  → jurisdiction + region
      - scope2_market, scope3_market,
        renewable_pct                      → jurisdiction only (region_id IS NULL)
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

        # Exact match
        for factor_year, factor_value in values:
            if factor_year == requested_year:
                return factor_value

        earliest_year, earliest_value = values[0]
        latest_year, latest_value = values[-1]

        # Before earliest year
        if requested_year < earliest_year:
            return earliest_value

        # After latest year
        if requested_year > latest_year:
            return latest_value

        # Interpolation within a gap
        lower_year = None
        lower_value = None
        upper_year = None
        upper_value = None

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
            (
                requested_year - lower_year
            )
            / (
                upper_year - lower_year
            )
        ) * (
            upper_value - lower_value
        )


    async def calculate(
        self,
        db: AsyncSession,
        request: ElectricityDetailedRequest,
    ) -> ElectricityDetailedResponse:
        # Resolve jurisdiction and region — from DB when project_id is given
        if request.project_id is not None:
            jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, request.project_id)
            region = await ProjectContextHelper.fetch_project_region(db, request.project_id)
        else:
            jurisdiction = request.jurisdiction  # type: ignore[assignment]
            region = request.region              # type: ignore[assignment]

        # Carry over date windows supplied by the caller.
        # The frontend passes either construction years or ops years depending on the call context.
        construction_start_year = request.construction_start_year
        construction_end_year = request.construction_end_year
        ops_start_year = request.ops_start_year
        ops_end_year = request.ops_end_year

        dataset_revision_id: Optional[UUID] = None

        if request.project_id is not None:
            dataset_revision_id = (
                await ProjectContextHelper.fetch_project_dataset_revision(
                    db,
                    request.project_id,
                )
            )

        factors = await self._fetch_factors(
            db,
            jurisdiction=jurisdiction,
            region=region,
            year=request.year,
            dataset_revision_id=dataset_revision_id,
        )

       
        ui_table_key = request.ui_table_key
        lb_mult = _LB_MULTIPLIERS[request.emission_source]
        mb_mult = _MB_MULTIPLIERS[request.emission_source]
        
        print(f"DEBUG: emission_source={request.emission_source}, lb_mult={lb_mult}, mb_mult={mb_mult}")

        # Convert quantity to MWh based on unit
        _unit_to_mwh: dict[str, float] = {"kWh": 0.001, "MWh": 1.0, "GWh": 1000.0}
        qty = request.quantity * _unit_to_mwh.get(request.unit, 1.0)

        # Total Grid + Offsite MWh for the year — SUMIFS resolved from activity_data.
        # Only needed for Grid Electricity (mb_mult = 1); skip the query otherwise.
        if mb_mult != 0 and request.project_stage_instance_id and request.project_option_id:
            print(f"DEBUG: Fetching SUMIFS total for project_stage_instance_id={request.project_stage_instance_id}, project_option_id={request.project_option_id}, year={request.year}, project_id={request.project_id}")
            total_yr_mwh: float = await self._fetch_sumifs_from_activity_data(
                db,
                project_stage_instance_id=request.project_stage_instance_id,
                project_option_id=request.project_option_id,
                year=request.year,
                project_id=request.project_id,
            )
            if total_yr_mwh == 0:
                print("DEBUG: SUMIFS query returned 0 total MWh for the year; using single-row quantity for total_yr_mwh.")
                total_yr_mwh = qty
        else:
            print("Fallback: skipping SUMIFS query; using single-row quantity for total_yr_mwh.")
            # Fallback: single-row calculation (no cross-row context available)
            total_yr_mwh = qty

        print(f"DEBUG: jurisdiction={jurisdiction}, region={region}, year={request.year}, qty={qty}, total_yr_mwh={total_yr_mwh}")

        f_s2_lb = factors.get("scope2_location")
        f_s3_lb = factors.get("scope3_location")

        f_s2_mb = factors.get("scope2_market")
        f_s3_mb = factors.get("scope3_market")
        # RPP defaults to 0 if missing (no renewable credit applied)
        rpp = factors.get("renewable_pct") or 0.0

        # Location-based: lb_mult × qty × factor
        # When lb_mult = 0 (Onsite Renewable), result is 0 regardless of factor availability.
        if lb_mult == 0:
            s2_lb: Optional[float] = 0.0
            s3_lb: Optional[float] = 0.0
        else:
            s2_lb = (lb_mult * qty * f_s2_lb) if f_s2_lb is not None else None
            s3_lb = (lb_mult * qty * f_s3_lb) if f_s3_lb is not None else None

        # Market-based:
        #   Grid Electricity (mb_mult = 1):
        #     net_mb_qty = qty - total_yr_mwh × RPP
        #     scope_mb   = net_mb_qty × factor
        #   Onsite / Offsite Renewable (mb_mult = 0): always 0
        if mb_mult == 0:
            s2_mb: Optional[float] = 0.0
            s3_mb: Optional[float] = 0.0
        else:
            net_mb_qty = qty - total_yr_mwh * rpp

            print(f"DEBUG: qty={qty}, total_yr_mwh={total_yr_mwh}, rpp={rpp}, net_mb_qty={net_mb_qty}")

            s2_mb = (mb_mult * net_mb_qty * f_s2_mb) if f_s2_mb is not None else None
            s3_mb = (mb_mult * net_mb_qty * f_s3_mb) if f_s3_mb is not None else None

            print(f"DEBUG: s2_mb={s2_mb}, s3_mb={s3_mb}, f_s2_mb={f_s2_mb}, f_s3_mb={f_s3_mb}" )


        lb_total = (s2_lb + s3_lb) if (s2_lb is not None and s3_lb is not None) else None
        mb_total = (s2_mb + s3_mb) if (s2_mb is not None and s3_mb is not None) else None

        print(f"DEBUG: lb_total={lb_total}, mb_total={mb_total}, s2_lb={s2_lb}, s3_lb={s3_lb}, s2_mb={s2_mb}, s3_mb={s3_mb}")

        return ElectricityDetailedResponse(
            project_id=request.project_id,
            jurisdiction=jurisdiction,
            region=region,
            emission_source=request.emission_source,
            year=request.year,
            quantity_mwh=qty,
            construction_start_year=construction_start_year,
            construction_end_year=construction_end_year,
            ops_start_year=ops_start_year,
            ops_end_year=ops_end_year,
            location_based_total_tco2e=_round(lb_total),
            market_based_total_tco2e=_round(mb_total),
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

    async def _fetch_sumifs_from_activity_data(
        self,
        db: AsyncSession,
        project_stage_instance_id: UUID,
        project_option_id: UUID,
        year: int,
        project_id: Optional[UUID] = None,
        ui_table_key: str = "electricity",
    ) -> float:
        """
        Replicates the Excel SUMIFS:
          SUMIFS([Quantity (MWh)], [Emission Source],
                 {"Grid Electricity","Offsite Renewable Electricity"}, [Year], year)

        Queries activity_data rows matching:
          - project_id (when provided)
          - project_stage_instance_id + project_option_id
          - ui_table_key = 'electricity', 'opEnergyElectricity', or 'electricity-mitigation'
          - extra_fields->>'emission_source' IN ('Grid Electricity', 'Offsite Renewable Electricity')
          - (extra_fields->>'year')::int = year

        Returns the total quantity_mwh sum (0.0 if no rows found).
        Rows stored with non-MWh units are normalised inline using the
        unit_display field (kWh → ×0.001, GWh → ×1000, else ×1.0).
        """
        sql = """
            SELECT COALESCE(
                SUM(
                    (ad.extra_fields->>'quantity_mwh')::numeric *
                    CASE ad.extra_fields->>'unit_display'
                        WHEN 'kWh' THEN 0.001
                        WHEN 'GWh' THEN 1000.0
                        ELSE 1.0
                    END
                ),
                0
            )::double precision AS total_mwh
            FROM activity_data ad
            WHERE
                ad.project_stage_instance_id = CAST(:instance_id AS uuid)
                AND ad.project_option_id = CAST(:option_id AS uuid)
                AND (
                    ad.ui_table_key = :ui_table_key
                    OR (
                        :ui_table_key = 'electricity-mitigation'
                        AND ad.ui_table_key LIKE 'electricity-mitigation%'
                    )
                )
                AND (ad.extra_fields->>'year')::int = :year
                AND ad.extra_fields->>'emission_source' IN (
                    'Grid Electricity',
                    'Offsite Renewable Electricity'
                )
        """
        params: dict = {
            "instance_id": str(project_stage_instance_id),
            "option_id": str(project_option_id),
            "year": year,
            "ui_table_key": str(ui_table_key),
        }
        if project_id is not None:
            sql += "\n                AND ad.project_id = CAST(:project_id AS uuid)"
            params["project_id"] = str(project_id)

        result = await db.execute(text(sql), params)
        row = result.fetchone()
        return float(row.total_mwh) if row and row.total_mwh is not None else 0.0

    # async def _fetch_factors(
    #     self,
    #     db: AsyncSession,
    #     jurisdiction: str,
    #     region: str,
    #     year: int,
    #     dataset_revision_id: Optional[UUID],
    # ) -> dict[str, float]:
    #     """
    #     Returns {factor_type_code: float_value} for the given jurisdiction/region/year.
    #     Missing factor types are absent from the dict (→ None in the response).
    #     """
    #     base_sql = """
    #         SELECT
    #             edf.factor_type_code,
    #             edf.value::double precision AS value
    #         FROM electric_decarb_factors edf
    #         JOIN jurisdictions j ON j.id = edf.jurisdiction_id
    #         LEFT JOIN grid_regions gr ON gr.id = edf.region_id
    #         WHERE
    #             edf.year = :year
    #             AND j.name = :jurisdiction
    #             AND (
    #                 (
    #                     edf.factor_type_code IN ('scope2_location', 'scope3_location')
    #                     AND gr.name = :region
    #                 )
    #                 OR
    #                 (
    #                     edf.factor_type_code IN ('scope2_market', 'scope3_market', 'renewable_pct')
    #                     AND edf.region_id IS NULL
    #                 )
    #             )
    #     """

    #     params: dict = {
    #         "year": year,
    #         "jurisdiction": jurisdiction,
    #         "region": region,
    #     }

    #     if dataset_revision_id is not None:
    #         base_sql += "\n                AND edf.dataset_revision_id = CAST(:dataset_revision_id AS uuid)"
    #         params["dataset_revision_id"] = str(dataset_revision_id)

    #     result = await db.execute(text(base_sql), params)

    #     return {
    #         row.factor_type_code: float(row.value)
    #         for row in result.fetchall()
    #         if row.value is not None
    #     }
    async def _fetch_factors(
        self,
        db: AsyncSession,
        jurisdiction: str,
        region: str,
        year: int,
        dataset_revision_id: Optional[UUID],
    ) -> dict[str, float]:
        """
        Returns factor values for the requested year.

        Rules:
        - Exact year available -> use exact value.
        - Year between two available years -> linear interpolation.
        - Year after latest available year -> use latest available value.
        - Year before earliest available year -> use earliest available value.
        """

        sql = """
            SELECT
                edf.factor_type_code,
                edf.year,
                edf.value::double precision AS value
            FROM electric_decarb_factors edf
            JOIN jurisdictions j
                ON j.id = edf.jurisdiction_id
            LEFT JOIN grid_regions gr
                ON gr.id = edf.region_id
            WHERE
                j.name = :jurisdiction
                AND (
                    (
                        edf.factor_type_code IN (
                            'scope2_location',
                            'scope3_location'
                        )
                        AND gr.name = :region
                    )
                    OR
                    (
                        edf.factor_type_code IN (
                            'scope2_market',
                            'scope3_market',
                            'renewable_pct'
                        )
                        AND edf.region_id IS NULL
                    )
                )
        """

        params: dict = {
            "jurisdiction": jurisdiction,
            "region": region,
        }

        if dataset_revision_id is not None:
            sql += """
                AND edf.dataset_revision_id =
                    CAST(:dataset_revision_id AS uuid)
            """
            params["dataset_revision_id"] = str(dataset_revision_id)

        sql += """
            ORDER BY
                edf.factor_type_code,
                edf.year
        """

        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        factor_history: dict[str, list[tuple[int, float]]] = {}

        for row in rows:
            factor_history.setdefault(
                row.factor_type_code,
                []
            ).append(
                (
                    int(row.year),
                    float(row.value),
                )
            )

        factors: dict[str, float] = {}

        for factor_type, values in factor_history.items():
            interpolated_value = self._interpolate_factor_value(
                requested_year=year,
                values=values,
            )

            if interpolated_value is not None:
                factors[factor_type] = interpolated_value

        return factors


_round = round_result



# Module-level singleton
calculator = ElectricityDetailedCalculator()
