# """
# services/grade34_construction_calculations.py

# Service for Grade 3/4 Detailed Level - Construction Stage (A5) emissions calculations.

# Based on Excel formulas from the 'MVP - Grade 1234' sheet,
# tables: tbl_detailed_level_calcs_construction and tbl_A4_calc_construction.

# === FORMULA REFERENCE ===

# tbl_detailed_level_calcs_construction (main output table)
# ---------------------------------------------------------
# Column: Emissions (tCO2e)
#   = SUM(Product Stage A1-3 + Transport Stage A4 + Construction Stage A5)

# Column: Product Stage (A1-3) Emissions (tCO2e)
#   = IF(Category="Materials", Qty * XLOOKUP(Jurisdiction+Source → Scope3 EF), 0)

# Column: Transport Stage (A4) Emissions (tCO2e)
#   = IF(Category IN ("Materials","Waste"),
#         TonnageConversion * SUMPRODUCT(distances[], EFs[]),
#     0)

# Column: Construction Stage (A5) Emissions (tCO2e)
#   = IF(Category="Electricity", Scope3,          ← #REF in Excel; use Scope3 only for now
#     IF(Category="Materials",   0,
#        Scope1 + Scope3))

# Column: Scope 1 Emissions (tCO2e)
#   = XLOOKUP(Jurisdiction+Category+SubCategory+Source → Scope1 EF) * Qty

# Column: Scope 3 Emissions (tCO2e)
#   = XLOOKUP(Jurisdiction+Category+SubCategory+Source → Scope3 EF) * Qty
#   + IF(Category IN ("Materials","Waste"), A4 transport emissions, 0)

# tbl_A4_calc_construction (intermediate A4 transport table)
# ----------------------------------------------------------
# Emissions Category     = IF(Category IN ("Materials","Waste"), Category, "")
# Emissions Source       = IF(Category IN ("Materials","Waste"), Source,   "")
# Tonnage Conversion     = IF(unit="t", Qty, Qty * XLOOKUP(Source → Density))
# Truck Transport Mode   = XLOOKUP(SubCategory → v_transport_distances_lookup.truck_transport_mode)
# Rail Transport Mode    = XLOOKUP(SubCategory → v_transport_distances_lookup.rail_transport_mode)
# Sea Transport Mode     = XLOOKUP(SubCategory → v_transport_distances_lookup.sea_transport_mode)
# Truck Distance (km)    = XLOOKUP(SubCategory → v_transport_distances_lookup.truck_km)
# Rail Distance (km)     = XLOOKUP(SubCategory → v_transport_distances_lookup.rail_km)
# Shipping Distance (km) = XLOOKUP(SubCategory → v_transport_distances_lookup.sea_km)
# Truck EF               = XLOOKUP(TruckMode → v_grade34_detailed_level.emission_factor_scope3)
# Rail EF                = XLOOKUP(RailMode  → v_grade34_detailed_level.emission_factor_scope3)
# Shipping EF            = XLOOKUP(SeaMode   → v_grade34_detailed_level.emission_factor_scope3)

# === DB VIEWS USED ===
#   v_grade34_detailed_level      — emission factors & scope EFs for Grade 3/4 rows
#   v_transport_distances_lookup  — transport modes & distances by jurisdiction + sub-category
#   v_densities_detailed_level    — material densities for unit-to-tonne conversion
# """

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_TRANSPORT_CATEGORIES = frozenset({"Materials", "Waste"})

_GRADE34_UNIT_ALIASES = {
    "ton": "t",
    "tons": "t",
    "tonne": "t",
    "tonnes": "t",
    "metric tonne": "t",
    "metric tonnes": "t",
}


def _grade34_factor_unit_code(unit: str) -> str:
    """Normalize common equivalent labels to the symbols used by dataset factors."""
    cleaned = " ".join(str(unit or "").strip().split())
    return _GRADE34_UNIT_ALIASES.get(cleaned.casefold(), cleaned)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class Grade34ConstructionRequest(BaseModel):
    """
    Input for a single Detailed Level - Construction Stage row.
    Matches user-entered columns from tbl_detailed_level_calcs_construction.
    """
    jurisdiction: str = Field(..., description="e.g. 'Australia'")
    emissions_category: str = Field(..., description="e.g. 'Fuels', 'Materials', 'Waste', 'Electricity'")
    emissions_sub_category: str = Field(..., description="e.g. 'Liquid Fuels (Static)'")
    emissions_source: str = Field(..., description="e.g. 'Diesel oil'")
    unit: str = Field(..., description="Unit of measure, e.g. 'kL', 't', 'm3'")
    quantity: float = Field(..., gt=0, description="Quantity in the stated unit")
    dataset_revision_id: Optional[UUID] = Field(
        None, description="Selected project dataset revision used for factor lookups"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "Australia",
                "emissions_category": "Materials",
                "emissions_sub_category": "Asphalt",
                "emissions_source": "Hot mix asphalt, 4%",
                "unit": "t",
                "quantity": 67,
            }
        }
    }


class A4TransportDetail(BaseModel):
    """
    Intermediate tbl_A4_calc_construction data exposed for transparency.
    Populated only when Emissions Category is 'Materials' or 'Waste'.
    """
    emissions_category: Optional[str] = None
    emissions_source: Optional[str] = None
    tonnage_conversion: Optional[float] = Field(None, description="Quantity converted to tonnes")

    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    shipping_transport_mode: Optional[str] = None

    truck_distance_km: Optional[float] = None
    rail_distance_km: Optional[float] = None
    shipping_distance_km: Optional[float] = None

    truck_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for truck mode")
    rail_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for rail mode")
    shipping_ef: Optional[float] = Field(None, description="tCO2e/t·km — Scope 3 EF for shipping mode")
    emissions_tco2e: Optional[float] = Field(
        None,
        description="Emissions (tCO2e) = IFERROR(TonnageConversion × SUMPRODUCT(distances, EFs), 0)",
    )


class Grade34ConstructionResponse(BaseModel):
    """
    Calculated emissions for a single Detailed Level - Construction Stage row.
    """
    # ── Echoed inputs ───────────────────────────────────────────────────────
    jurisdiction: str
    emissions_category: str
    emissions_sub_category: str
    emissions_source: str
    unit: str
    quantity: float

    # ── Emission factors retrieved from v_grade34_detailed_level ────────────
    scope1_ef: Optional[float] = Field(None, description="Scope 1 EF (tCO2e/UoM) from view")
    scope3_ef: Optional[float] = Field(None, description="Scope 3 EF (tCO2e/UoM) from view")

    # ── Calculated emissions (tCO2e) ────────────────────────────────────────
    scope1_emissions_tco2e: Optional[float] = Field(
        None, description="Scope 1 = Scope1 EF × Qty"
    )
    scope3_emissions_tco2e: Optional[float] = Field(
        None,
        description=(
            "Scope 3 = (Scope3 EF × Qty) + A4 transport emissions "
            "(for Materials/Waste only)"
        ),
    )
    product_stage_a1_a3_tco2e: float = Field(
        description="A1-3: Scope3 EF × Qty for Materials; 0 otherwise"
    )
    transport_stage_a4_tco2e: float = Field(
        description=(
            "A4: TonnageConversion × SUMPRODUCT(distances, EFs) for Materials only; "
            "0 for all other categories including Waste "
            "(Waste transport is computed in A4 calc table but flows into Scope 3)"
        )
    )
    construction_stage_a5_tco2e: float = Field(
        description="A5: Materials → 0; All other categories (incl. Electricity) → Scope1 + Scope3"
    )
    total_emissions_tco2e: float = Field(
        description="Total = A1-3 + A4 + A5"
    )

    # ── Intermediate A4 transport detail ────────────────────────────────────
    a4_transport_detail: Optional[A4TransportDetail] = Field(
        None, description="Intermediate tbl_A4_calc_construction data (Materials/Waste only)"
    )
    # ── Warnings (non-fatal data gaps) ──────────────────────────────────────
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

class Grade34ConstructionCalculator:
    """
    Replicates the Excel tbl_detailed_level_calcs_construction formulas
    using PostgreSQL views for all lookup data.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
    ) -> Grade34ConstructionResponse:

        # ── 1. Fetch emission factors from v_grade34_detailed_level ─────────
        # Mirrors Excel IFERROR behaviour: if the 4-key lookup (Jurisdiction +
        # Category + Sub-Category + Source + UoM) finds no row, scope1/scope3 EFs
        # default to None/0 and a data_warning is recorded.  This can happen when
        # the sub-category is not populated for a row in background_grade_metrics.
        data_warnings: list[str] = []
        ef_row = await self._fetch_emission_factors(db, request)
        if not ef_row:
            data_warnings.append(
                f"No EF row found in v_grade34_detailed_level for "
                f"Jurisdiction='{request.jurisdiction}', "
                f"Category='{request.emissions_category}', "
                f"Sub-Category='{request.emissions_sub_category}', "
                f"Source='{request.emissions_source}', "
                f"Unit='{request.unit}'. "
                f"Scope 1 & Scope 3 base emissions defaulted to 0. "
                f"Check that emission_factor_scope1 / emission_factor_scope3 values "
                f"and Emissions Sub-Category are correctly loaded in background_grade_metrics."
            )

        scope1_ef = self._f(ef_row.get("emission_factor_scope1")) if ef_row else None
        scope3_ef = self._f(ef_row.get("emission_factor_scope3")) if ef_row else None
        qty = request.quantity

        # ── 2. Scope 1 & Scope 3 base emissions ────────────────────────────
        scope1_base = (scope1_ef or 0.0) * qty
        scope3_base = (scope3_ef or 0.0) * qty

        # ── 3. A4 transport (Materials and Waste only) ──────────────────────
        a4_detail: Optional[A4TransportDetail] = None
        a4_tco2e = 0.0

        if request.emissions_category in _TRANSPORT_CATEGORIES:
            a4_detail, a4_tco2e = await self._calculate_a4(db, request, qty)

        # ── 4. Column formulas ──────────────────────────────────────────────
        cat = request.emissions_category

        # Product Stage A1-3
        # Formula: IF(Category="Materials", Qty × XLOOKUP(Jurisdiction+Source → Scope3 EF), 0)
        # Uses 2-key lookup (Jurisdiction + Emissions Source only), matching the Excel formula.
        if cat == "Materials":
            scope3_ef_by_source = await self._fetch_scope3_ef_by_source_only(db, request)
            a1_a3 = (scope3_ef_by_source or 0.0) * qty
        else:
            a1_a3 = 0.0

        # Transport Stage A4 column
        # Formula: IFERROR(IF(Category="Materials", TonnageConversion × SUMPRODUCT(...), 0), 0)
        # Only "Materials" shows in the A4 column.
        # "Waste" transport is computed in _calculate_a4 but flows into Scope 3 only.
        a4_column = a4_tco2e if cat == "Materials" else 0.0

        # Scope 3 total
        # Formula: (Scope3 EF × Qty) + tbl_A4_calc_construction[Emissions (tCO2e)]
        # The A4 calc table is populated for both Materials AND Waste, so both add to Scope 3.
        scope3_total = scope3_base + (a4_tco2e if cat in _TRANSPORT_CATEGORIES else 0.0)

        # Construction Stage A5
        # Formula: IF(Category="Materials", 0, Scope1 + Scope3)
        # Electricity no longer has a special branch — it follows the same
        # Scope1 + Scope3 path as all other non-Materials categories.
        if cat == "Materials":
            a5 = 0.0
        else:
            a5 = scope1_base + scope3_total

        total = a1_a3 + a4_column + a5

        return Grade34ConstructionResponse(
            jurisdiction=request.jurisdiction,
            emissions_category=request.emissions_category,
            emissions_sub_category=request.emissions_sub_category,
            emissions_source=request.emissions_source,
            unit=request.unit,
            quantity=qty,
            scope1_ef=scope1_ef,
            scope3_ef=scope3_ef,
            scope1_emissions_tco2e=round_result(scope1_base),
            scope3_emissions_tco2e=round_result(scope3_total),
            product_stage_a1_a3_tco2e=a1_a3,
            transport_stage_a4_tco2e=a4_column,
            construction_stage_a5_tco2e=a5,
            total_emissions_tco2e=round_result(total),
            a4_transport_detail=a4_detail,
            data_warnings=data_warnings,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # A4 transport sub-calculation
    # ─────────────────────────────────────────────────────────────────────────

    async def _calculate_a4(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
        qty: float,
    ) -> tuple[Optional[A4TransportDetail], float]:
        """
        Replicates tbl_A4_calc_construction row for Materials/Waste categories.

        Returns (A4TransportDetail, a4_tco2e).
        """

        # ── 3a. Tonnage conversion ──────────────────────────────────────────
        # If unit is already 't', use qty directly.
        # Otherwise, lookup density and multiply: qty × density → tonnes.
        if _grade34_factor_unit_code(request.unit).casefold() == "t":
            tonnage = qty
            density_used = None
        else:
            density_used = await self._fetch_density(db, request)
            if density_used is not None:
                tonnage = qty * density_used
            else:
                # Cannot convert — treat as raw qty (best-effort)
                tonnage = qty

        # ── 3b. Transport distances for the sub-category ───────────────────
        td = await self._fetch_transport_distances(db, request)

        truck_mode = td.get("truck_transport_mode") if td else None
        rail_mode  = td.get("rail_transport_mode")  if td else None
        sea_mode   = td.get("sea_transport_mode")   if td else None
        truck_km   = self._f(td.get("truck_km"))    if td else None
        rail_km    = self._f(td.get("rail_km"))     if td else None
        sea_km     = self._f(td.get("sea_km"))      if td else None

        # ── 3c. Transport EFs from v_grade34_detailed_level ─────────────────
        # EF lookup: XLOOKUP(transport_mode → Emissions Source → Scope3 EF)
        truck_ef   = await self._fetch_transport_ef(db, request, truck_mode)
        rail_ef    = await self._fetch_transport_ef(db, request, rail_mode)
        sea_ef     = await self._fetch_transport_ef(db, request, sea_mode)

        # ── 3d. SUMPRODUCT(distances × EFs) → A4 tCO2e ─────────────────────
        # Formula: TonnageConversion × SUMPRODUCT([distances], [EFs])
        a4 = tonnage * (
            ((truck_km or 0.0) * (truck_ef or 0.0))
            + ((rail_km  or 0.0) * (rail_ef  or 0.0))
            + ((sea_km   or 0.0) * (sea_ef   or 0.0))
        )

        detail = A4TransportDetail(
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
            emissions_tco2e=round_result(a4),
        )

        return detail, a4

    # ─────────────────────────────────────────────────────────────────────────
    # DB queries
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_emission_factors(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
    ) -> Optional[dict]:
        """
        Query v_grade34_detailed_level for Scope 1 & Scope 3 EFs.
        Lookup key: Jurisdiction + Emissions Category + Emissions Sub-Category + Emissions Source + UoM.
        The UoM filter is essential because the view groups by unit — the same source can have
        multiple rows (e.g. m3, GJ) with different EF values.
        """        
        query = text("""
            SELECT
                "emission_factor_scope1",
                "emission_factor_scope3"
            FROM v_grade34_detailed_level AS factor_row
            WHERE "Jurisdiction"          = :jurisdiction
              AND "Emissions Category"    = :emissions_category
              AND "Emissions Sub-Category" = :emissions_sub_category
              AND "Emissions Source"      = :emissions_source
              AND "UoM"                  = :unit
              AND (
                    CAST(:dataset_revision_id AS text) IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)
              )
            ORDER BY
                (to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)) DESC NULLS LAST
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":          request.jurisdiction,
            "emissions_category":    request.emissions_category,
            "emissions_sub_category": request.emissions_sub_category,
            "emissions_source":      request.emissions_source,
            "unit":                  _grade34_factor_unit_code(request.unit),
            "dataset_revision_id": str(request.dataset_revision_id) if request.dataset_revision_id else None,
        })
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _fetch_scope3_ef_by_source_only(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
    ) -> Optional[float]:
        """
        Query v_grade34_detailed_level for Scope 3 EF using only Jurisdiction + Emissions Source + UoM.
        Used for Product Stage (A1-3) when Category is 'Materials'.
        Matches Excel formula:
          XLOOKUP(1, (Jurisdiction=$C$58)*(Source=[@Source]), Scope3 EF)
        The UoM filter prevents picking a row for a different unit of the same source.
        """
        query = text("""
            SELECT "emission_factor_scope3"
            FROM v_grade34_detailed_level AS factor_row
            WHERE "Jurisdiction"     = :jurisdiction
              AND "Emissions Source" = :emissions_source
              AND "UoM"             = :unit
              AND (
                    CAST(:dataset_revision_id AS text) IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)
              )
            ORDER BY
                (to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)) DESC NULLS LAST
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":     request.jurisdiction,
            "emissions_source": request.emissions_source,
            "unit":             _grade34_factor_unit_code(request.unit),
            "dataset_revision_id": str(request.dataset_revision_id) if request.dataset_revision_id else None,
        })
        row = result.fetchone()
        if row is None:
            return None
        return self._f(row._mapping["emission_factor_scope3"])

    async def _fetch_density(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
    ) -> Optional[float]:
        """
        Query v_densities_detailed_level for the density of an emissions source.
        Lookup key: Emissions Source (+ optional Jurisdiction filter, preferring specific over global).
        Returns density as float, or None if not found.
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
        if row is None:
            return None
        return self._f(row._mapping["Density"])

    async def _fetch_transport_distances(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
    ) -> Optional[dict]:
        """
        Query v_transport_distances_lookup for transport modes and distances.
        Lookup key: Jurisdiction + Emissions Sub-Category.
        Uses the existing view column names: jurisdiction, emissions_sub_category,
        truck_km, rail_km, sea_km, truck_transport_mode, rail_transport_mode, sea_transport_mode.
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
            WHERE jurisdiction        = :jurisdiction
              AND emissions_sub_category = :emissions_sub_category
              AND is_active = TRUE
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":          request.jurisdiction,
            "emissions_sub_category": request.emissions_sub_category,
        })
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _fetch_transport_ef(
        self,
        db: AsyncSession,
        request: Grade34ConstructionRequest,
        transport_mode: Optional[str],
    ) -> Optional[float]:
        """
        Look up the Scope 3 EF for a transport mode by matching it against
        the Emissions Source column in v_grade34_detailed_level.
        Returns None when transport_mode is None or empty.
        """
        if not transport_mode:
            return None

        query = text("""
            SELECT "emission_factor_scope3"
            FROM v_grade34_detailed_level AS factor_row
            WHERE "Jurisdiction"     = :jurisdiction
              AND "Emissions Source" = :transport_mode
              AND (
                    CAST(:dataset_revision_id AS text) IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' IS NULL
                    OR to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)
              )
            ORDER BY
                (to_jsonb(factor_row)->>'dataset_revision_id' = CAST(:dataset_revision_id AS text)) DESC NULLS LAST
            LIMIT 1
        """)
        result = await db.execute(query, {
            "jurisdiction":   request.jurisdiction,
            "transport_mode": transport_mode,
            "dataset_revision_id": str(request.dataset_revision_id) if request.dataset_revision_id else None,
        })
        row = result.fetchone()
        if row is None:
            return None
        return self._f(row._mapping["emission_factor_scope3"])

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
calculator = Grade34ConstructionCalculator()
