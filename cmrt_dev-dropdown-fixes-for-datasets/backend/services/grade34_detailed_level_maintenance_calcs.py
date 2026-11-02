# """
# services/grade34_detailed_level_maintenance_calcs.py
#
# Service for Detailed Level - Maintenance, Repair, Replacement and Refurbishment
# (B2-B5) Stage emissions calculations.
#
# Based on Excel formulas from the 'MVP - Grade 1234' sheet,
# tables: tbl_detailed_level_calcs_maintenance88 and tbl_B1_calc_inuse_transport89.
#
# === FORMULA REFERENCE ===
#
# Project-level inputs (from Excel header section):
#   Operations Start Date  → C243
#   Operations End Date    → C244
#   Reference Period       → C245 = MIN(C244 - C243, 50)
#
# tbl_detailed_level_calcs_maintenance88 (main output table)
# ----------------------------------------------------------
# Column: Emissions (tCO2e)
#   = SUM([@[Scope 1 Emissions (tCO2e)]], [@[Scope 3 Emissions (tCO2e)]])
#
# Column: Scope 1 Emissions (tCO2e)
#   = IFERROR(
#       XLOOKUP(1,
#         (Jurisdiction = tbl_detailed_level[Jurisdiction]) *
#         (Category    = tbl_detailed_level[Emissions Category]) *
#         (SubCategory = tbl_detailed_level[Emissions Sub-Category]) *
#         (Source      = tbl_detailed_level[Emissions Source]),
#         tbl_detailed_level[Scope 1 EF] *
#           IFS(Period="Annual",               $C$245 * Quantity,
#               Period="Total Operational Life", Quantity)
#       ), 0)
#
# Column: Scope 3 Emissions (tCO2e)
#   = IFNA(IFERROR(
#       XLOOKUP(..., tbl_detailed_level[Scope 3 EF] *
#         IFS(Period="Annual", $C$245*Qty, Period="Total Operational Life", Qty)
#       ), 0), 0)
#   + IFERROR(
#       tbl_B1[Tonnage Conversion] * SUMPRODUCT([distances], [EFs]),
#     0)
#
# tbl_B1_calc_inuse_transport89 (intermediate transport table)
# ------------------------------------------------------------
# Same structure as tbl_A4_calc_construction (Construction Stage):
#   Emissions Category     = IF(Category IN ("Materials","Waste"), Category, "")
#   Emissions Source       = IF(Category IN ("Materials","Waste"), Source, "")
#   Tonnage Conversion     = IF(unit="t", eff_qty, eff_qty × density)
#   Truck/Rail/Sea Mode    = XLOOKUP(SubCategory → v_transport_distances_lookup)
#   Truck/Rail/Sea km      = XLOOKUP(SubCategory → v_transport_distances_lookup)
#   Truck/Rail/Sea EF      = XLOOKUP(mode → v_grade34_detailed_level.scope3_ef)
#
# NOTE: effective_qty = reference_period × quantity  when Period = "Annual"
#                     = quantity                      when Period = "Total Operational Life"
#       Tonnage conversion uses effective_qty so transport emissions also scale with period.
#
# === DB VIEWS USED ===
#   v_grade34_detailed_level      — Scope 1 & Scope 3 emission factors
#   v_transport_distances_lookup  — transport modes & distances (Materials/Waste only)
#   v_densities_detailed_level    — material densities for unit-to-tonne conversion
# """

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_TRANSPORT_CATEGORIES = frozenset({"Materials", "Waste"})
_REFERENCE_PERIOD_CAP = 50  # Excel formula: MIN(end - start, 50)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class Grade34MaintenanceRequest(BaseModel):
    """
    Input for a single Detailed Level - Maintenance (B2-5) Stage row.
    Matches tbl_detailed_level_calcs_maintenance88 user-entered columns
    plus the project-level header inputs.
    """
    # ── Project-level inputs ─────────────────────────────────────────────────
    jurisdiction: str = Field(..., description="e.g. 'Australia'")
    ops_start: int = Field(
        ..., description="Operations start year — cell C243 in Excel, e.g. 2029"
    )
    ops_end: int = Field(
        ..., description="Operations end year — cell C244 in Excel, e.g. 2100"
    )

    # ── Row-level inputs ─────────────────────────────────────────────────────
    emissions_category: str = Field(
        ..., description="e.g. 'Fuels', 'Materials', 'Waste', 'Electricity'"
    )
    emissions_sub_category: str = Field(
        ..., description="e.g. 'Liquid Fuels (Static)', 'Asphalt'"
    )
    emissions_source: str = Field(
        ..., description="e.g. 'Diesel oil', 'Hot mix asphalt, 4%'"
    )
    period: Literal["Annual", "Total Operational Life"] = Field(
        ...,
        description=(
            "'Annual' — emissions apply every year; effective qty = reference_period × quantity. "
            "'Total Operational Life' — one-off total; effective qty = quantity."
        ),
    )
    unit: str = Field(..., description="Unit of measure, e.g. 'kL', 't', 'm2'")
    quantity: float = Field(..., gt=0, description="Quantity per event / per year in the stated unit")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ops_end <= self.ops_start:
            raise ValueError(
                "ops_end must be greater than ops_start"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "ops_start": 2029,
                "ops_end": 2100,
                "emissions_category": "Fuels",
                "emissions_sub_category": "Liquid Fuels (Static)",
                "emissions_source": "Diesel oil",
                "period": "Annual",
                "unit": "kL",
                "quantity": 50,
            }
        }
    }


class B1TransportDetail(BaseModel):
    """
    Intermediate tbl_B1_calc_inuse_transport89 data exposed for transparency.
    Populated only when Emissions Category is 'Materials' or 'Waste'.
    Mirrors the A4 transport table from the Construction Stage.
    """
    emissions_category: Optional[str] = None
    emissions_source: Optional[str] = None
    tonnage_conversion: Optional[float] = Field(
        None, description="Effective quantity converted to tonnes"
    )

    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    shipping_transport_mode: Optional[str] = None

    truck_distance_km: Optional[float] = None
    rail_distance_km: Optional[float] = None
    shipping_distance_km: Optional[float] = None

    truck_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for truck mode")
    rail_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for rail mode")
    shipping_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for shipping")
    transport_emissions_tco2e: Optional[float] = Field(
        None,
        description="IFERROR(TonnageConversion × SUMPRODUCT(distances, EFs), 0)",
    )


class Grade34MaintenanceResponse(BaseModel):
    """
    Calculated emissions for a single Detailed Level - Maintenance (B2-5) Stage row.
    """
    # ── Echoed inputs ────────────────────────────────────────────────────────
    jurisdiction: str
    ops_start: int
    ops_end: int
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    period: str
    unit: str
    quantity: float

    # ── Computed project-level value ─────────────────────────────────────────
    reference_period: float = Field(
        ...,
        description="MIN(ops_end - ops_start, 50) — cell C245 in Excel",
    )
    effective_quantity: float = Field(
        ...,
        description=(
            "Period-adjusted quantity: "
            "reference_period × quantity (Annual) or quantity (Total Operational Life)"
        ),
    )

    # ── Calculated emissions (tCO2e) ─────────────────────────────────────────
    scope1_emissions_tco2e: float = Field(
        ..., description="Scope 1 EF × effective_quantity (IFERROR → 0)"
    )
    scope3_emissions_tco2e: float = Field(
        ...,
        description=(
            "(Scope 3 EF × effective_quantity) "
            "+ transport emissions for Materials/Waste (IFNA/IFERROR → 0)"
        ),
    )
    total_emissions_tco2e: float = Field(
        ..., description="Scope 1 + Scope 3"
    )

    # ── Intermediate B1 transport detail ─────────────────────────────────────
    b1_transport_detail: Optional[B1TransportDetail] = Field(
        None, description="Intermediate tbl_B1_calc_inuse_transport89 data (Materials/Waste only)"
    )

    # ── Warnings (non-fatal data gaps) ───────────────────────────────────────
    data_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal data warnings, e.g. missing EF lookups. "
            "Mirrors Excel IFERROR/IFNA behaviour — missing values default to 0."
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────

class Grade34MaintenanceCalculator:
    """
    Replicates the Excel tbl_detailed_level_calcs_maintenance88 formulas
    using PostgreSQL views for all lookup data.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: Grade34MaintenanceRequest,
    ) -> Grade34MaintenanceResponse:
        data_warnings: list[str] = []

        # ── 1. Reference Period (cell C245) ───────────────────────────────────
        # Excel: =MIN(C244 - C243, 50)
        reference_period = min(
            request.ops_end - request.ops_start,
            _REFERENCE_PERIOD_CAP,
        )

        # ── 2. Effective quantity — IFS on Period ─────────────────────────────
        # Excel IFS:
        #   Period="Annual"               → $C$245 * Quantity
        #   Period="Total Operational Life" → Quantity
        if request.period == "Annual":
            effective_qty = reference_period * request.quantity
        else:
            effective_qty = request.quantity

        # ── 3. Fetch Scope 1 & Scope 3 EFs from v_grade34_detailed_level ─────
        # Lookup key: Jurisdiction + Category + Sub-Category + Source + UoM
        # Mirrors Excel 4-way XLOOKUP.  IFERROR/IFNA → 0 when not found.
        ef_row = await self._fetch_emission_factors(db, request)
        if not ef_row:
            data_warnings.append(
                f"No EF row found in v_grade34_detailed_level for "
                f"Jurisdiction='{request.jurisdiction}', "
                f"Category='{request.emissions_category}', "
                f"Sub-Category='{request.emissions_sub_category}', "
                f"Source='{request.emissions_source}', "
                f"Unit='{request.unit}'. "
                f"Scope 1 & Scope 3 base emissions defaulted to 0."
            )

        scope1_ef = self._f(ef_row.get("emission_factor_scope1")) if ef_row else None
        scope3_ef = self._f(ef_row.get("emission_factor_scope3")) if ef_row else None

        # ── 4. Scope 1 = EF × effective_qty ──────────────────────────────────
        scope1 = (scope1_ef or 0.0) * effective_qty

        # ── 5. Transport: B1 calc table (Materials / Waste only) ─────────────
        # Mirrors tbl_A4_calc_construction from the Construction Stage.
        # Tonnage conversion uses effective_qty so transport scales with period.
        b1_detail: Optional[B1TransportDetail] = None
        transport_tco2e = 0.0

        if request.emissions_category in _TRANSPORT_CATEGORIES:
            b1_detail, transport_tco2e = await self._calculate_b1(
                db, request, effective_qty
            )

        # ── 6. Scope 3 = (EF × effective_qty) + transport ────────────────────
        scope3_base = (scope3_ef or 0.0) * effective_qty
        scope3 = scope3_base + transport_tco2e

        # ── 7. Total = Scope 1 + Scope 3 ─────────────────────────────────────
        total = scope1 + scope3

        return Grade34MaintenanceResponse(
            jurisdiction=request.jurisdiction,
            ops_start=request.ops_start,
            ops_end=request.ops_end,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            period=request.period,
            unit=request.unit,
            quantity=request.quantity,
            reference_period=float(reference_period),
            effective_quantity=effective_qty,
            scope1_emissions_tco2e=round_result(scope1),
            scope3_emissions_tco2e=round_result(scope3),
            total_emissions_tco2e=round_result(total),
            b1_transport_detail=b1_detail,
            data_warnings=data_warnings,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # B1 transport sub-calculation
    # ─────────────────────────────────────────────────────────────────────────

    async def _calculate_b1(
        self,
        db: AsyncSession,
        request: Grade34MaintenanceRequest,
        effective_qty: float,
    ) -> tuple[Optional[B1TransportDetail], float]:
        """
        Replicates tbl_B1_calc_inuse_transport89 for Materials/Waste categories.
        effective_qty is already period-adjusted; used as the base for tonnage conversion.
        Returns (B1TransportDetail, transport_tco2e).
        """
        # ── Tonnage conversion ────────────────────────────────────────────────
        # IF(unit="t", effective_qty, effective_qty × density)
        if request.unit.lower() == "t":
            tonnage = effective_qty
        else:
            density = await self._fetch_density(db, request)
            tonnage = effective_qty * density if density is not None else effective_qty

        # ── Transport distances (by jurisdiction + sub-category) ──────────────
        td = await self._fetch_transport_distances(db, request)

        truck_mode = td.get("truck_transport_mode") if td else None
        rail_mode  = td.get("rail_transport_mode")  if td else None
        sea_mode   = td.get("sea_transport_mode")   if td else None
        truck_km   = self._f(td.get("truck_km"))    if td else None
        rail_km    = self._f(td.get("rail_km"))     if td else None
        sea_km     = self._f(td.get("sea_km"))      if td else None

        # ── Transport EFs from v_grade34_detailed_level ───────────────────────
        truck_ef = await self._fetch_transport_ef(db, request.jurisdiction, truck_mode)
        rail_ef  = await self._fetch_transport_ef(db, request.jurisdiction, rail_mode)
        sea_ef   = await self._fetch_transport_ef(db, request.jurisdiction, sea_mode)

        # ── SUMPRODUCT(distances × EFs) × tonnage ────────────────────────────
        transport_tco2e = tonnage * (
            ((truck_km or 0.0) * (truck_ef or 0.0))
            + ((rail_km  or 0.0) * (rail_ef  or 0.0))
            + ((sea_km   or 0.0) * (sea_ef   or 0.0))
        )

        detail = B1TransportDetail(
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
            transport_emissions_tco2e=transport_tco2e,
        )
        return detail, transport_tco2e

    # ─────────────────────────────────────────────────────────────────────────
    # DB queries
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_emission_factors(
        self,
        db: AsyncSession,
        request: Grade34MaintenanceRequest,
    ) -> Optional[dict]:
        """
        Query v_grade34_detailed_level for Scope 1 & Scope 3 EFs.
        Lookup key: Jurisdiction + Category + Sub-Category + Source + UoM.
        Mirrors the 4-way XLOOKUP from the Excel Scope 1 / Scope 3 formulas.

        Fallback: if the 4-key lookup (with sub-category) finds no row — which happens when
        emissions_subcategory_id is NULL in background_grade_metrics — retry without the
        sub-category filter.  This mirrors Excel XLOOKUP behaviour where an empty cell in
        the lookup array matches the empty sub-category in the source data.
        """
        params = {
            "jurisdiction":           request.jurisdiction,
            "emissions_category":     request.emissions_category,
            "emissions_sub_category": request.emissions_sub_category,
            "emissions_source":       request.emissions_source,
            "unit":                   request.unit,
        }

        # ── 4-key lookup (preferred) ─────────────────────────────────────────
        query_4key = text("""
            SELECT
                emission_factor_scope1,
                emission_factor_scope3
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction"           = :jurisdiction
              AND "Emissions Category"     = :emissions_category
              AND "Emissions Sub-Category" = :emissions_sub_category
              AND "Emissions Source"       = :emissions_source
              AND "UoM"                   = :unit
            LIMIT 1
        """)
        result = await db.execute(query_4key, params)
        row = result.fetchone()
        if row:
            return dict(row._mapping)

        # ── 3-key fallback (sub-category not linked in DB) ───────────────────
        query_3key = text("""
            SELECT
                emission_factor_scope1,
                emission_factor_scope3
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction"       = :jurisdiction
              AND "Emissions Category" = :emissions_category
              AND "Emissions Source"   = :emissions_source
              AND "UoM"               = :unit
            LIMIT 1
        """)
        result = await db.execute(query_3key, params)
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _fetch_density(
        self,
        db: AsyncSession,
        request: Grade34MaintenanceRequest,
    ) -> Optional[float]:
        """
        Query v_densities_detailed_level for material density.
        Prefers jurisdiction-specific row; falls back to 'Global'.
        """
        query = text("""
            SELECT "Density"
            FROM v_densities_detailed_level
            WHERE "Emissions Source" = :emissions_source
              AND ("Jurisdiction" = :jurisdiction OR "Jurisdiction" = 'Global')
            ORDER BY
                CASE WHEN "Jurisdiction" = :jurisdiction THEN 0 ELSE 1 END
            LIMIT 1
        """)
        result = await db.execute(query, {
            "emissions_source": request.emissions_source,
            "jurisdiction":     request.jurisdiction,
        })
        row = result.fetchone()
        return self._f(row._mapping["Density"]) if row else None

    async def _fetch_transport_distances(
        self,
        db: AsyncSession,
        request: Grade34MaintenanceRequest,
    ) -> Optional[dict]:
        """
        Query v_transport_distances_lookup for modes and distances.
        Lookup key: Jurisdiction + Emissions Sub-Category.
        """
        query = text("""
            SELECT
                truck_transport_mode,
                rail_transport_mode,
                sea_transport_mode,
                truck_km,
                rail_km,
                sea_km
            FROM v_transport_distances_lookup
            WHERE jurisdiction           = :jurisdiction
              AND emissions_sub_category = :emissions_sub_category
              AND is_active = TRUE
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":           request.jurisdiction,
            "emissions_sub_category": request.emissions_sub_category,
        })
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _fetch_transport_ef(
        self,
        db: AsyncSession,
        jurisdiction: str,
        transport_mode: Optional[str],
    ) -> Optional[float]:
        """
        Look up Scope 3 EF for a transport mode by matching it against
        Emissions Source in v_grade34_detailed_level.
        Returns None when transport_mode is None or empty.
        """
        if not transport_mode:
            return None
        query = text("""
            SELECT emission_factor_scope3
            FROM v_grade34_detailed_level
            WHERE "Jurisdiction"     = :jurisdiction
              AND "Emissions Source" = :transport_mode
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":  jurisdiction,
            "transport_mode": transport_mode,
        })
        row = result.fetchone()
        return self._f(row._mapping["emission_factor_scope3"]) if row else None

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _f(value) -> Optional[float]:
        """Safely convert Decimal / None to float."""
        if value is None:
            return None
        return float(value)


# Singleton instance used by the router
calculator = Grade34MaintenanceCalculator()
