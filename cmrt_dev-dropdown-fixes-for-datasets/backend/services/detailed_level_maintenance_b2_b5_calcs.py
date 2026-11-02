# """
# Detailed Level Maintenance (B2-B5) Emissions Calculations

# Calculates Scope 1 and Scope 3 emissions for maintenance, repair, replacement,
# and refurbishment (B2-B5) activities during operations.

# Table: tbl_detailed_level_calcs_maintenance88
# Intermediate table: tbl_B1_calc_inuse_transport89 (for Materials/Waste transport)

# Formulas:
# - Reference Period = MIN(ops_end - ops_start, 50)
# - Scope 1 = Scope1_EF × IFS(Annual → Ref_Period × Qty, Lifetime → Qty)
# - Scope 3 = Scope3_EF × IFS(Annual → Ref_Period × Qty, Lifetime → Qty) + Transport (for Materials/Waste)
# - Total = Scope 1 + Scope 3

# Data sources:
# - v_grade34_detailed_level: Scope 1 & Scope 3 factors, transport EFs
# - v_transport_distances_lookup: Transport modes & distances by sub-category
# - v_densities_detailed_level: Material densities for unit-to-tonne conversion
# """

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_MIN_YEAR = 1900
_MAX_YEAR = 2200
_MAX_REFERENCE_PERIOD = 50
_TRANSPORT_CATEGORIES = frozenset({"Materials", "Waste"})
_ANNUAL_PERIOD_VALUES = frozenset({"annual average", "average annual life", "annual"})
_TOTAL_LIFE_PERIOD_VALUES = frozenset({"total operational life", "total"})


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────


class DetailedMaintenanceB2B5Request(BaseModel):
    """
    Input for a single Detailed Level - Maintenance (B2-B5) Stage row.
    Matches user-entered columns from tbl_detailed_level_calcs_maintenance88.
    """

    jurisdiction: str = Field(..., description="e.g. 'Australia'")
    project_id: Optional[UUID] = Field(
        None,
        description="Project ID to derive operations start/end years. Required when period is 'Annual'.",
    )
    ops_start: Optional[int] = Field(
        None,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations start year (e.g. 2029). Auto-derived from project_id if not provided.",
    )
    ops_end: Optional[int] = Field(
        None,
        ge=_MIN_YEAR,
        le=_MAX_YEAR,
        description="Operations end year (e.g. 2100). Auto-derived from project_id if not provided.",
    )

    # Row data
    emissions_category: str = Field(
        ..., description="e.g. 'Materials', 'Waste', 'Electricity', 'Fuels'"
    )
    emissions_sub_category: str = Field(
        ..., description="e.g. 'Asphalt', 'Vehicles', 'Liquid Fuels (Static)'"
    )
    emissions_source: str = Field(
        ..., description="e.g. 'Hot mix asphalt, 4%', 'Diesel oil'"
    )
    period: str = Field(
        ...,
        description="Period type: 'Annual', 'Annual Average', 'Average Annual Life', 'Total Operational Life', or 'Total' (case-insensitive).",
    )
    unit: str = Field(..., description="Unit of measure, e.g. 'kL', 't', 'm3'")
    quantity: float = Field(
        ..., gt=0, description="Quantity in the stated unit"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "project_id": "6df1ce4f-7c5f-4950-b99e-0262b9f1fbe6",
                "ops_start": None,
                "ops_end": None,
                "emissions_category": "Materials",
                "emissions_sub_category": "Asphalt",
                "emissions_source": "Hot mix asphalt, 4%",
                "period": "Annual",
                "unit": "t",
                "quantity": 50.0,
            }
        }
    }


class TransportDetail(BaseModel):
    """
    Intermediate transport calculation data (Materials/Waste only).
    Populates from tbl_B1_calc_inuse_transport89 intermediate table.
    """

    emissions_category: Optional[str] = None
    emissions_source: Optional[str] = None
    tonnage_conversion: Optional[float] = Field(
        None, description="Quantity converted to tonnes"
    )

    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    shipping_transport_mode: Optional[str] = None

    truck_distance_km: Optional[float] = None
    rail_distance_km: Optional[float] = None
    shipping_distance_km: Optional[float] = None

    truck_ef: Optional[float] = Field(
        None, description="tCO2e/t·km — Scope 3 EF for truck mode"
    )
    rail_ef: Optional[float] = Field(
        None, description="tCO2e/t·km — Scope 3 EF for rail mode"
    )
    shipping_ef: Optional[float] = Field(
        None, description="tCO2e/t·km — Scope 3 EF for shipping mode"
    )
    emissions_tco2e: Optional[float] = Field(
        None,
        description="Emissions (tCO2e) = IFERROR(TonnageConversion × SUMPRODUCT(distances, EFs), 0)",
    )


class DetailedMaintenanceB2B5Response(BaseModel):
    """
    Calculated emissions for a single Detailed Level - Maintenance (B2-B5) row.
    """

    # ── Echoed inputs ───────────────────────────────────────────────────────
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

    # ── Emission factors retrieved from v_grade34_detailed_level ────────────
    scope1_ef: Optional[float] = Field(
        None, description="Scope 1 EF (tCO2e/UoM) from view"
    )
    scope3_ef: Optional[float] = Field(
        None, description="Scope 3 EF (tCO2e/UoM) from view"
    )

    # ── Calculated emissions (tCO2e) ────────────────────────────────────────
    scope1_emissions_tco2e: Optional[float] = Field(
        None, description="Scope 1 = Scope1 EF × Adjusted Qty"
    )
    scope3_emissions_tco2e: Optional[float] = Field(
        None,
        description="Scope 3 = (Scope3 EF × Adjusted Qty) + transport (for Materials/Waste)",
    )
    total_emissions_tco2e: Optional[float] = Field(
        None, description="Total = Scope 1 + Scope 3"
    )

    # ── Intermediate transport detail ────────────────────────────────────────
    transport_detail: Optional[TransportDetail] = Field(
        None,
        description="Intermediate tbl_B1_calc_inuse_transport89 data (Materials/Waste only)",
    )

    # ── Warnings (non-fatal data gaps) ──────────────────────────────────────
    data_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal data warnings, e.g. missing EF/density lookups. "
            "Mirrors Excel IFERROR/IFNA behaviour — missing values default to 0."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────


class DetailedMaintenanceB2B5Calculator:
    """
    Replicates the Excel tbl_detailed_level_calcs_maintenance88 formulas
    using PostgreSQL views for all lookup data.
    """

    def _f(self, v: any) -> Optional[float]:
        """Convert Decimal/numeric to float, handle None."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        return float(v) if v is not None else None

    @staticmethod
    def _normalize_period(period: str) -> str:
        """Normalize period string to canonical form."""
        value = (period or "").strip().lower()
        if value in _ANNUAL_PERIOD_VALUES:
            return "annual average"
        if value in _TOTAL_LIFE_PERIOD_VALUES:
            return "total operational life"
        raise ValueError(
            f"Invalid period '{period}'. Expected one of: 'Annual', 'Annual Average', "
            "'Average Annual Life', 'Total Operational Life', or 'Total'."
        )

    async def calculate(
        self,
        db: AsyncSession,
        request: DetailedMaintenanceB2B5Request,
    ) -> DetailedMaintenanceB2B5Response:
        """
        Calculate maintenance emissions for a single (B2-B5) row.
        """
        data_warnings: list[str] = []

        # ── 0. Resolve operational years from project_id if needed ─────────
        ops_start = request.ops_start
        ops_end = request.ops_end
        
        if ops_start is None or ops_end is None:
            if request.project_id is None:
                raise ValueError(
                    "Either provide both ops_start and ops_end, or provide project_id "
                    "to derive operational years automatically."
                )
            project = await ProjectContextHelper.fetch_project(db, request.project_id)
            ops_start, ops_end = ProjectContextHelper.get_operational_years(project)

        # ── 1. Calculate reference period ────────────────────────────────────
        reference_period = min(ops_end - ops_start, _MAX_REFERENCE_PERIOD)

        # ── 2. Fetch emission factors from v_grade34_detailed_level ─────────
        ef_row = await self._fetch_emission_factors(db, request)
        if not ef_row:
            data_warnings.append(
                f"No EF row found in v_grade34_detailed_level for "
                f"Jurisdiction='{request.jurisdiction}', "
                f"Category='{request.emissions_category}', "
                f"Sub-Category='{request.emissions_sub_category}', "
                f"Source='{request.emissions_source}'. "
                f"Scope 1 & Scope 3 emissions defaulted to 0."
            )

        scope1_ef = self._f(ef_row.get("emission_factor_scope1")) if ef_row else None
        scope3_ef = self._f(ef_row.get("emission_factor_scope3")) if ef_row else None

        # ── 3. Calculate adjusted quantity based on Period ───────────────────
        period_normalized = self._normalize_period(request.period)
        if period_normalized == "annual average":
            adjusted_qty = reference_period * request.quantity
        else:  # "Total Operational Life"
            adjusted_qty = request.quantity

        # ── 4. Scope 1 & Scope 3 base emissions ────────────────────────────
        scope1_emissions = (scope1_ef or 0.0) * adjusted_qty
        scope3_base = (scope3_ef or 0.0) * adjusted_qty

        # ── 5. Transport emissions (Materials and Waste only) ───────────────
        transport_detail: Optional[TransportDetail] = None
        transport_tco2e = 0.0

        if request.emissions_category in _TRANSPORT_CATEGORIES:
            transport_detail, transport_tco2e = await self._calculate_transport(
                db, request, adjusted_qty
            )

        scope3_emissions = scope3_base + transport_tco2e

        # ── 6. Total emissions ──────────────────────────────────────────────
        total_emissions = (
            (scope1_emissions or 0.0) + (scope3_emissions or 0.0)
        )

        return DetailedMaintenanceB2B5Response(
            jurisdiction=request.jurisdiction,
            ops_start=ops_start,
            ops_end=ops_end,
            reference_period=reference_period,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            period=request.period,
            unit=request.unit,
            quantity=request.quantity,
            scope1_ef=scope1_ef,
            scope3_ef=scope3_ef,
            scope1_emissions_tco2e=round_result(scope1_emissions)
            if scope1_emissions is not None
            else None,
            scope3_emissions_tco2e=round_result(scope3_emissions)
            if scope3_emissions is not None
            else None,
            total_emissions_tco2e=round_result(total_emissions)
            if total_emissions is not None
            else None,
            transport_detail=transport_detail,
            data_warnings=data_warnings,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Transport sub-calculation
    # ─────────────────────────────────────────────────────────────────────────

    async def _calculate_transport(
        self,
        db: AsyncSession,
        request: DetailedMaintenanceB2B5Request,
        adjusted_qty: float,
    ) -> tuple[Optional[TransportDetail], float]:
        """
        Replicates tbl_B1_calc_inuse_transport89 row for Materials/Waste categories.
        Returns (TransportDetail, transport_tco2e).
        """

        # ── 1. Tonnage conversion ────────────────────────────────────────────
        if request.unit.lower() == "t":
            tonnage = adjusted_qty
        else:
            density = await self._fetch_density(db, request)
            tonnage = adjusted_qty * (density or 1.0)

        # ── 2. Transport distances for the sub-category ─────────────────────
        td = await self._fetch_transport_distances(db, request)

        truck_mode = td.get("truck_transport_mode") if td else None
        rail_mode = td.get("rail_transport_mode") if td else None
        sea_mode = td.get("sea_transport_mode") if td else None
        truck_km = self._f(td.get("truck_km")) if td else None
        rail_km = self._f(td.get("rail_km")) if td else None
        sea_km = self._f(td.get("sea_km")) if td else None

        # ── 3. Transport EFs from v_grade34_detailed_level ─────────────────
        truck_ef = await self._fetch_transport_ef(db, request.jurisdiction, truck_mode)
        rail_ef = await self._fetch_transport_ef(db, request.jurisdiction, rail_mode)
        sea_ef = await self._fetch_transport_ef(db, request.jurisdiction, sea_mode)

        # ── 4. SUMPRODUCT(distances × EFs) → transport tCO2e ────────────────
        transport = tonnage * (
            ((truck_km or 0.0) * (truck_ef or 0.0))
            + ((rail_km or 0.0) * (rail_ef or 0.0))
            + ((sea_km or 0.0) * (sea_ef or 0.0))
        )

        detail = TransportDetail(
            emissions_category=request.emissions_category,
            emissions_source=request.emissions_source,
            tonnage_conversion=tonnage,
            truck_transport_mode=truck_mode,
            rail_transport_mode=rail_mode,
            shipping_transport_mode=sea_mode,
            truck_distance_km=truck_km,
            rail_distance_km=rail_km,
            shipping_distance_km=sea_km,
            truck_ef=truck_ef,
            rail_ef=rail_ef,
            shipping_ef=sea_ef,
            emissions_tco2e=round_result(transport)
            if transport is not None
            else None,
        )

        return detail, transport

    # ─────────────────────────────────────────────────────────────────────────
    # Lookups
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_emission_factors(
        self, db: AsyncSession, request: DetailedMaintenanceB2B5Request
    ) -> Optional[dict]:
        """Fetch Scope 1 and Scope 3 factors from v_grade34_detailed_level."""
        sql = """
            SELECT 
                emission_factor_scope1,
                emission_factor_scope3
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
                "jurisdiction": request.jurisdiction,
                "emissions_category": request.emissions_category,
                "emissions_sub_category": request.emissions_sub_category,
                "emissions_source": request.emissions_source,
            },
        )
        row = result.fetchone()
        if row is None:
            return None
        return {
            "emission_factor_scope1": row[0],
            "emission_factor_scope3": row[1],
        }

    async def _fetch_density(
        self, db: AsyncSession, request: DetailedMaintenanceB2B5Request
    ) -> Optional[float]:
        """Fetch density from v_densities_detailed_level to convert unit to tonnes."""
        sql = """
            SELECT density
            FROM v_densities_detailed_level
            WHERE jurisdiction = :jurisdiction
              AND emissions_source = :emissions_source
            LIMIT 1
        """
        result = await db.execute(
            text(sql),
            {
                "jurisdiction": request.jurisdiction,
                "emissions_source": request.emissions_source,
            },
        )
        row = result.fetchone()
        return self._f(row[0]) if row else None

    async def _fetch_transport_distances(
        self, db: AsyncSession, request: DetailedMaintenanceB2B5Request
    ) -> Optional[dict]:
        """
        Fetch transport modes and distances from v_transport_distances_lookup
        for the given (jurisdiction, sub-category).
        """
        sql = """
            SELECT 
                truck_transport_mode,
                rail_transport_mode,
                sea_transport_mode,
                truck_km,
                rail_km,
                sea_km
            FROM v_transport_distances_lookup
            WHERE jurisdiction = :jurisdiction
              AND emissions_sub_category = :emissions_sub_category
            LIMIT 1
        """
        result = await db.execute(
            text(sql),
            {
                "jurisdiction": request.jurisdiction,
                "emissions_sub_category": request.emissions_sub_category,
            },
        )
        row = result.fetchone()
        if row is None:
            return None
        return {
            "truck_transport_mode": row[0],
            "rail_transport_mode": row[1],
            "sea_transport_mode": row[2],
            "truck_km": row[3],
            "rail_km": row[4],
            "sea_km": row[5],
        }

    async def _fetch_transport_ef(
        self,
        db: AsyncSession,
        jurisdiction: str,
        transport_mode: Optional[str],
    ) -> Optional[float]:
        """
        Fetch Scope 3 EF from v_grade34_detailed_level for a given transport mode.
        XLOOKUP: transport_mode (Emissions Source) → Scope3 EF
        """
        if not transport_mode:
            return None

        sql = """
            SELECT emission_factor_scope3
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction" = :jurisdiction
              AND "Emissions Source" = :emissions_source
            LIMIT 1
        """
        result = await db.execute(
            text(sql),
            {
                "jurisdiction": jurisdiction,
                "emissions_source": transport_mode,
            },
        )
        row = result.fetchone()
        return self._f(row[0]) if row else None


# Module-level singleton
calculator = DetailedMaintenanceB2B5Calculator()
