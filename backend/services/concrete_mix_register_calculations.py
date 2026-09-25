"""
services/concrete_mix_register_calculations.py

Stateless Concrete Register (MVP) calculation service.

Replicates the Excel formulas from tbl_concrete_register_mix.
No data is stored — results are calculated on-the-fly and returned.

Request/Response models are defined here (following the grade1_asset_calculations pattern).

Part 1 — Mix header inputs
    Mix ID label   : free text (e.g. "AXJ739")
    Mix Type       : "Ready-mix" | "Precast" | "Shotcrete"
    Strength (MPa) : positive integer
    Target SCM %   : 0–100 (percent, not fraction)
    Volume (m3)    : used volume on project

Part 2 — Per-component calculations
────────────────────────────────────
Binder set: {"General Purpose Cement", "Fly Ash", "GGBF Slag"}
binder_total = SUM(qty) for materials in BINDER_SET
scm_frac     = scm_pct / 100   (None → no SCM adjustment applied)

Quantity with SCM target applied:
    General Purpose Cement : binder_total × (1 − scm_frac)
    Fly Ash                : binder_total × scm_frac × 0.25
    GGBF Slag              : binder_total × scm_frac × 0.75
    all other materials    : quantity_kg_m3  (unchanged)

Component EF (tCO2e/m3):
    = XLOOKUP(material_name → scope3_ef) × scm_qty / 1000
      ↑ scope3_ef from v_grade34_detailed_level (tCO2e/UoM, UoM usually t)
      ↑ / 1000 converts quantity from kg/m3 to t/m3

Transport EF (tCO2e/m3):
    distances from v_transport_distances_lookup keyed on
        jurisdiction='Australia' AND emissions_sub_category
    EFs from v_grade34_detailed_level keyed on transport mode name
    = SUMPRODUCT([truck_km, rail_km, sea_km], [truck_ef, rail_ef, sea_ef])
      × scm_qty / 1000

GWP A1-A3 (tCO2e/m3) = SUM(component_ef + transport_ef) for all rows
Total emissions (tCO2e) = GWP × volume_m3

Part 3 — EF label
    "{mix_id_label} {mix_type} Concrete {strength_mpa} MPa {scm_pct}% SCM"
    e.g. "AXJ739 Precast Concrete 65 MPa 50% SCM"
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services._calc_utils import round_result
from services.project_context_helper import ProjectContextHelper


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_JURISDICTION = "Australia"

# Both current frontend names and canonical names are included so SCM
# adjustment works before and after the frontend label update.
_BINDER_SET = frozenset({
    "General purpose cement", "General Purpose Cement",
    "Fly ash",                "Fly Ash",
    "GGBF slag",
})

_GP_CEMENT_NAMES = frozenset({"General purpose cement", "General Purpose Cement"})
_FLY_ASH_NAMES   = frozenset({"Fly ash", "Fly Ash"})
_GGBF_SLAG_NAMES = frozenset({"GGBF slag"})

# BAU view component codes that belong to the cementitious trio and are
# recalculated in the simplified path from total_cementitious + SCM target.
_BAU_BINDER_COMPONENT_CODES = frozenset({
    "general_purpose_cement",
    "fly_ash",
    "ggbf_slag",
})

_MIX_TYPES = frozenset({"Ready-mix", "Precast", "Shotcrete"})

# BAU default concrete mix data is now sourced from the database view
# v_bau_default_concrete_mix (created by migration cr05_view_bau_default_concrete_mix).
# The view unpivots concrete_mix_designs (one row per component × strength grade)
# and joins concrete_mix_assumptions for the FA cap (default_max_fly_ash_pct).
# _fetch_bau_grade_data() below queries this view at runtime.

# Maps frontend material_name → (db_src, display_sub_cat, transport_sub_cat, em_cat)
#   db_src           : exact "Emissions Source" value in v_grade34_detailed_level
#   display_sub_cat  : echoed as emissions_sub_category in response (None = blank, e.g. Fine Aggregates)
#   transport_sub_cat: key for v_transport_distances_lookup (None = no transport for this material)
#   em_cat           : echoed as emissions_category in response
_MATERIAL_CONFIG: dict[str, tuple[str, Optional[str], Optional[str], str]] = {
    # Binder / cementitious materials — "Concrete components" transport (truck=350, sea=3400)
    # Both lowercase (legacy) and Title Case (current frontend) variants included.
    "General purpose cement":            ("General purpose cement",      "Concrete components", "Concrete components",            "Materials"),
    "General Purpose Cement":            ("General purpose cement",      "Concrete components", "Concrete components",            "Materials"),
    "Fly ash":                           ("Fly ash",                     "Concrete components", "Concrete components",            "Materials"),
    "Fly Ash":                           ("Fly ash",                     "Concrete components", "Concrete components",            "Materials"),
    "GGBF slag":                         ("GGBF slag",                   "Concrete components", "Concrete components",            "Materials"),
    "Silica Fume":                       ("Silica fume",                 "Concrete components", "Concrete components",            "Materials"),
    # Admixture — uses "Concrete components" transport (truck=350, sea=3,400).
    # Grade34 places "General concrete admixtures" under Emissions Sub-Category = "Concrete components",
    # and the transport distances table has no "Globally manufactured" sub-category row.
    # James confirmed: transport lookup key is Emissions Sub-Category (not the material name column).
    "Admixture":                         ("General concrete admixtures", "Concrete components", "Concrete components", "Materials"),
    "General Concrete Admixtures":       ("General concrete admixtures", "Concrete components", "Concrete components", "Materials"),
    # Fine Aggregates — "Aggregate" transport (truck=40), same as Coarse Aggregates
    "Fine Aggregates":                   ("Fine Aggregates",             "Aggregate",           "Aggregate",                      "Materials"),
    # Other aggregates — "Aggregate" transport (truck=40)
    "Coarse Aggregates":                 ("Coarse Aggregates",           "Aggregate",           "Aggregate",                      "Materials"),
    "Recycled Aggregates":               ("Recycled Aggregates",         "Aggregate",           "Aggregate",                      "Materials"),
    "Manufactured sand":                 ("Manufactured sand",           "Aggregate",           "Aggregate",                      "Materials"),
    # Water — "Water Use" classification, no transport (0 km in Excel)
    "Mains Water":                       ("Mains Water",                 "Water Use",           None,                             "Water"),
    "Mains water":                       ("Mains Water",                 "Water Use",           None,                             "Water"),
    "On-site recycled & captured water": ("Off-site recycled water",     "Water Use",           None,                             "Water"),
    "Onsite Recycled / Captured Water":  ("Off-site recycled water",     "Water Use",           None,                             "Water"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class ConcreteMixMaterialInput(BaseModel):
    """One component row for a concrete mix (Part 2 user input)."""

    material_name: str = Field(
        ...,
        description=(
            "One of the fixed concrete mix materials, "
            "e.g. 'General purpose cement', 'Fly ash', 'GGBF slag', 'Fine Aggregates'."
        ),
    )
    quantity_kg_m3: float = Field(..., ge=0, description="Quantity in kg per m3 of concrete")


class ConcreteMixCalculateRequest(BaseModel):
    """
    Input for one concrete mix design calculation.

    The endpoint accepts either a single object or a list of these.
    """

    project_id: UUID = Field(..., description="Project this mix belongs to")

    # Part 1 — mix header
    mix_id_label: str = Field(..., min_length=1, max_length=100, description="e.g. 'AXJ739'")
    mix_type: str = Field(..., description="'Ready-mix' | 'Precast' | 'Shotcrete'")
    strength_mpa: int = Field(..., gt=0, description="Compressive strength in MPa")
    scm_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="SCM substitution target as a percentage (0–100). Omit to skip SCM adjustment.",
    )
    volume_m3: float = Field(..., gt=0, description="Volume of this mix used on project (m3)")

    # Part 2 — component materials
    materials: List[ConcreteMixMaterialInput] = Field(..., min_length=1)

    @field_validator("mix_type")
    @classmethod
    def validate_mix_type(cls, v: str) -> str:
        if v not in _MIX_TYPES:
            raise ValueError(f"mix_type must be one of {sorted(_MIX_TYPES)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "ad056efb-8f93-43cb-b750-bb622f6d48ea",
                "mix_id_label": "AXJ739",
                "mix_type": "Precast",
                "strength_mpa": 65,
                "scm_pct": 50,
                "volume_m3": 500,
                "materials": [
                    {"material_name": "General purpose cement", "quantity_kg_m3": 400},
                    {"material_name": "Fly ash",                "quantity_kg_m3": 10},
                    {"material_name": "GGBF slag",              "quantity_kg_m3": 20},
                    {"material_name": "Fine Aggregates",        "quantity_kg_m3": 830},
                    {"material_name": "Coarse Aggregates",      "quantity_kg_m3": 970},
                    {"material_name": "Mains Water",            "quantity_kg_m3": 180},
                    {"material_name": "Admixture",              "quantity_kg_m3": 2},
                ],
            }
        }
    }


class ConcreteMixMaterialResult(BaseModel):
    """Fully calculated row for one concrete mix component (all Excel columns)."""

    # Echoed inputs (emissions_category / emissions_sub_category populated by backend)
    emissions_category: str
    emissions_sub_category: Optional[str]
    material_name: str
    quantity_kg_m3: float

    # SCM adjustment
    quantity_scm_applied: float = Field(
        description="SCM-adjusted quantity (kg/m3). Equals input for non-binder materials."
    )

    # Component EF
    scope3_ef: Optional[float] = Field(None, description="Scope 3 EF (tCO2e/UoM) from v_grade34_detailed_level")
    component_ef_tco2e_m3: float = Field(description="= scope3_ef × quantity_scm_applied / 1000")

    # Transport distances & modes
    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    shipping_transport_mode: Optional[str] = None
    truck_km: Optional[float] = None
    rail_km: Optional[float] = None
    shipping_km: Optional[float] = None

    # Transport EFs (tCO2e/t·km)
    truck_ef: Optional[float] = None
    rail_ef: Optional[float] = None
    shipping_ef: Optional[float] = None

    # Transport EF (tCO2e/m3)
    transport_ef_tco2e_m3: float = Field(
        description="= SUMPRODUCT([distances], [EFs]) × quantity_scm_applied / 1000"
    )

    # Row total
    total_ef_tco2e_m3: float = Field(description="= component_ef_tco2e_m3 + transport_ef_tco2e_m3")

    data_warnings: List[str] = Field(default_factory=list)


class ConcreteMixCalculateResponse(BaseModel):
    """
    Full on-the-fly calculation result for one concrete mix design.

    Stage breakdown (tCO2e/m3):
      component_stage_ef_tco2e_m3   = SUM(component_ef_tco2e_m3)  across all material rows  (A1)
      transport_stage_ef_tco2e_m3   = SUM(transport_ef_tco2e_m3)  across all material rows  (A2)
      production_stage_ef_tco2e_m3  = SUM(concrete_mix_production.emissions_kgco2e_m3) / 1000  (A3)
      gwp_a1a3_tco2e_m3             = component + transport + production
      transport_a4_ef_tco2e_m3      = a4_truck_km × a4_truck_ef × a4_tonnage_conversion  (A4)
      total_emissions_tco2e         = (gwp_a1a3 + a4_ef) × volume_m3

    A4 sub-category: "Precast concrete" if mix_type=Precast, else "Concrete in-situ"
    Concrete density (tonnage conversion): looked up from v_densities_detailed_level
      (Emissions Source = 'Concrete production process') — 2.4 t/m3.

    ef_label (Part 3) = "{mix_id_label} {mix_type} Concrete {strength_mpa} MPa {scm_pct}% SCM"
    """

    project_id: UUID
    mix_id_label: str
    mix_type: str
    strength_mpa: int
    scm_pct: Optional[float] = None
    volume_m3: float

    # Stage-level breakdown (tCO2e/m3)
    component_stage_ef_tco2e_m3: float = Field(
        description="Component Stage EF (tCO2e/m3) — SUM of component_ef_tco2e_m3 across all material rows"
    )
    transport_stage_ef_tco2e_m3: float = Field(
        description="Transport Stage EF (tCO2e/m3) — SUM of transport_ef_tco2e_m3 across all material rows"
    )
    production_stage_ef_tco2e_m3: float = Field(
        description=(
            "Production Stage EF (tCO2e/m3) — SUM(concrete_mix_production.emissions_kgco2e_m3) / 1000. "
            "Fixed AusLCI-derived reference value, independent of mix design."
        )
    )

    # GWP A1-A3 totals
    gwp_a1a3_tco2e_m3: float = Field(
        description="GWP A1-A3 (tCO2e/m3) = component + transport + production stage EFs"
    )
    gwp_a1a3_kgco2e_m3: float = Field(
        description="Carbon intensity (kgCO2e/m3) = gwp_a1a3_tco2e_m3 × 1000"
    )

    # Transport Stage A4 — delivery of finished concrete to site
    a4_sub_category: str = Field(
        description="'Precast concrete' if Precast mix, otherwise 'Concrete in-situ'"
    )
    a4_truck_transport_mode: Optional[str] = Field(
        None, description="Truck transport mode name from v_transport_distances_lookup"
    )
    a4_truck_km: Optional[float] = Field(
        None, description="Truck distance (km) from v_transport_distances_lookup"
    )
    a4_truck_ef: Optional[float] = Field(
        None, description="Truck EF (tCO2e/t·km) from v_grade34_detailed_level"
    )
    a4_tonnage_conversion: Optional[float] = Field(
        None, description="Concrete density (t/m3) from v_densities_detailed_level — used to convert m3 to tonnes"
    )
    transport_a4_ef_tco2e_m3: float = Field(
        description="Transport Stage A4 EF (tCO2e/m3) = a4_truck_km × a4_truck_ef × a4_tonnage_conversion"
    )

    total_emissions_tco2e: float = Field(
        description="Total project emissions (tCO2e) = (gwp_a1a3_tco2e_m3 + transport_a4_ef_tco2e_m3) × volume_m3"
    )

    # Part 3 — EF label
    ef_label: str = Field(
        description="Grade 3-4 dataset emission-factor label, e.g. 'AXJ739 Precast Concrete 65 MPa 50% SCM'"
    )

    # Per-material breakdown
    material_breakdown: List[ConcreteMixMaterialResult]

    data_warnings: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Calculator service
# ─────────────────────────────────────────────────────────────────────────────

class ConcreteMixCalculator:
    """
    Stateless service for concrete mix design emission factor calculations.

    All lookups come from DB views (v_grade34_detailed_level,
    v_transport_distances_lookup).  No data is written to the database.
    """

    async def calculate(
        self,
        db: AsyncSession,
        request: ConcreteMixCalculateRequest,
    ) -> ConcreteMixCalculateResponse:
        """Calculate emissions for a single concrete mix design."""

        self._validate_inputs(request)

        dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(
            db, request.project_id
        )
        if not dataset_revision_id:
            raise ValueError(
                f"Could not resolve dataset_revision_id for project {request.project_id}. "
                f"Ensure either ProjectDatasetRevision assignment exists or DEFAULT dataset revision is available."
            )

        scm_frac: Optional[float] = (
            request.scm_pct / 100.0 if request.scm_pct is not None else None
        )

        binder_total = sum(
            m.quantity_kg_m3
            for m in request.materials
            if m.material_name in _BINDER_SET
        )

        material_results: List[ConcreteMixMaterialResult] = []
        all_warnings: List[str] = []

        for mat in request.materials:
            row = await self._calculate_material_row(
                db,
                mat,
                binder_total,
                scm_frac,
                dataset_revision_id,
            )
            material_results.append(row)
            all_warnings.extend(row.data_warnings)

        # Stage-level aggregates
        component_stage = round_result(sum(r.component_ef_tco2e_m3 for r in material_results))
        transport_stage = round_result(sum(r.transport_ef_tco2e_m3 for r in material_results))
        production_stage = round_result(await self._fetch_production_stage_ef(db, dataset_revision_id))

        gwp_a1a3 = round_result(component_stage + transport_stage + production_stage)

        # Transport Stage A4 — delivery of finished concrete to site
        a4_sub_cat = self._a4_sub_category(request.mix_type)
        a4_td = await self._fetch_transport_distances(db, a4_sub_cat, dataset_revision_id)
        if a4_td is None:
            all_warnings.append(
                f"No A4 transport distances found for sub-category='{a4_sub_cat}'. "
                f"A4 transport EF defaulted to 0."
            )
        a4_truck_mode = a4_td.get("truck_transport_mode") if a4_td else None
        a4_truck_km   = self._f(a4_td.get("truck_km"))    if a4_td else None
        a4_truck_ef   = await self._fetch_transport_ef(db, a4_truck_mode, dataset_revision_id)
        a4_density    = await self._fetch_concrete_density(db)
        if a4_density is None:
            all_warnings.append(
                "Concrete density not found in v_densities_detailed_level. "
                "A4 transport EF defaulted to 0."
            )
        a4_ef = round_result(
            (a4_truck_km or 0.0) * (a4_truck_ef or 0.0) * (a4_density or 0.0)
        )

        # Keep A1-A3 fields as documented; include A4 only in total emissions.
        gwp_a1a3_kg = round_result(gwp_a1a3 * 1000)
        product_stage_total = round_result(gwp_a1a3 + a4_ef)

        total_em = round_result(product_stage_total * request.volume_m3)

        ef_label = self._build_ef_label(
            request.mix_id_label,
            request.mix_type,
            request.strength_mpa,
            request.scm_pct,
        )

        return ConcreteMixCalculateResponse(
            project_id=request.project_id,
            mix_id_label=request.mix_id_label,
            mix_type=request.mix_type,
            strength_mpa=request.strength_mpa,
            scm_pct=request.scm_pct,
            volume_m3=request.volume_m3,
            component_stage_ef_tco2e_m3=component_stage,
            transport_stage_ef_tco2e_m3=transport_stage,
            production_stage_ef_tco2e_m3=production_stage,
            gwp_a1a3_tco2e_m3=gwp_a1a3,
            gwp_a1a3_kgco2e_m3=gwp_a1a3_kg,
            a4_sub_category=a4_sub_cat,
            a4_truck_transport_mode=a4_truck_mode,
            a4_truck_km=a4_truck_km,
            a4_truck_ef=a4_truck_ef,
            a4_tonnage_conversion=a4_density,
            transport_a4_ef_tco2e_m3=a4_ef,
            total_emissions_tco2e=total_em,
            ef_label=ef_label,
            material_breakdown=material_results,
            data_warnings=all_warnings,
        )

    async def calculate_batch(
        self,
        db: AsyncSession,
        requests: List[ConcreteMixCalculateRequest],
    ) -> List[ConcreteMixCalculateResponse]:
        """Calculate emissions for multiple concrete mix designs."""
        results = []
        for req in requests:
            results.append(await self.calculate(db, req))
        return results

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_inputs(self, request: ConcreteMixCalculateRequest) -> None:
        if not request.materials:
            raise ValueError("At least one material row is required.")

    # ── A4 sub-category helper ────────────────────────────────────────────────

    @staticmethod
    def _a4_sub_category(mix_type: str) -> str:
        """Return the transport A4 sub-category for the given mix type."""
        if mix_type == "Precast":
            return "Precast concrete"
        return "Concrete in-situ"

    # ── Part 3 — EF label ─────────────────────────────────────────────────────

    def _build_ef_label(
        self,
        mix_id_label: str,
        mix_type: str,
        strength_mpa: int,
        scm_pct: Optional[float],
    ) -> str:
        if scm_pct is not None:
            return f"{mix_id_label} {mix_type} Concrete {strength_mpa} MPa {int(round(scm_pct))}% SCM"
        return f"{mix_id_label} {mix_type} Concrete {strength_mpa} MPa"

    # ── SCM-adjusted quantity ──────────────────────────────────────────────────

    def _scm_adjusted_qty(
        self,
        material_name: str,
        qty: float,
        binder_total: float,
        scm_frac: Optional[float],
    ) -> float:
        if qty == 0:
            return 0.0
        if scm_frac is None or material_name not in _BINDER_SET:
            return qty
        if material_name in _GP_CEMENT_NAMES:
            return binder_total * (1.0 - scm_frac)
        if material_name in _FLY_ASH_NAMES:
            return binder_total * scm_frac * 0.25
        if material_name in _GGBF_SLAG_NAMES:
            return binder_total * scm_frac * 0.75
        return qty

    # ── DB view lookups ───────────────────────────────────────────────────────

    async def _grade34_has_dataset_revision_column(self, db: AsyncSession) -> bool:
        """Return True when v_grade34_detailed_level exposes dataset_revision_id."""
        cached = getattr(self, "_grade34_has_dataset_revision_column_cache", None)
        if cached is not None:
            return cached

        result = await db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'v_grade34_detailed_level'
                      AND column_name = 'dataset_revision_id'
                ) AS has_col
            """)
        )
        row = result.fetchone()
        has_col = bool(row._mapping["has_col"]) if row else False
        setattr(self, "_grade34_has_dataset_revision_column_cache", has_col)
        return has_col

    async def _fetch_component_ef(
        self,
        db: AsyncSession,
        material_name: str,
        dataset_revision_id: Optional[UUID] = None,
    ) -> Optional[float]:
        has_dataset_revision_col = await self._grade34_has_dataset_revision_column(db)
        if has_dataset_revision_col and dataset_revision_id is not None:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :src
                      AND (
                        dataset_revision_id = CAST(:dataset_revision_id AS uuid)
                        OR dataset_revision_id IS NULL
                      )
                    ORDER BY
                        (dataset_revision_id = CAST(:dataset_revision_id AS uuid)) DESC,
                        dataset_revision_id DESC NULLS LAST
                    LIMIT 1
                """),
                {
                    "jur": _JURISDICTION,
                    "src": material_name,
                    "dataset_revision_id": str(dataset_revision_id),
                },
            )
        elif has_dataset_revision_col:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :src
                      AND dataset_revision_id IS NULL
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "src": material_name},
            )
        else:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :src
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "src": material_name},
            )
        row = result.fetchone()
        return self._f(row._mapping["emission_factor_scope3"]) if row else None

    async def _fetch_transport_distances(
        self,
        db: AsyncSession,
        emissions_sub_category: str,
        dataset_revision_id: Optional[UUID] = None,
    ) -> Optional[dict]:
        if dataset_revision_id is not None:
            result = await db.execute(
                text("""
                    SELECT
                        truck_transport_mode,
                        rail_transport_mode,
                        sea_transport_mode,
                        truck_km,
                        rail_km,
                        sea_km
                    FROM v_transport_distances_lookup
                    WHERE jurisdiction           = :jur
                      AND emissions_sub_category = :sub
                      AND is_active              = TRUE
                      AND (
                        dataset_revision_id = CAST(:dataset_revision_id AS uuid)
                        OR dataset_revision_id IS NULL
                      )
                    ORDER BY
                        (dataset_revision_id = CAST(:dataset_revision_id AS uuid)) DESC,
                        dataset_revision_id DESC NULLS LAST
                    LIMIT 1
                """),
                {
                    "jur": _JURISDICTION,
                    "sub": emissions_sub_category,
                    "dataset_revision_id": str(dataset_revision_id),
                },
            )
        else:
            result = await db.execute(
                text("""
                    SELECT
                        truck_transport_mode,
                        rail_transport_mode,
                        sea_transport_mode,
                        truck_km,
                        rail_km,
                        sea_km
                    FROM v_transport_distances_lookup
                    WHERE jurisdiction           = :jur
                      AND emissions_sub_category = :sub
                      AND is_active              = TRUE
                      AND dataset_revision_id IS NULL
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "sub": emissions_sub_category},
            )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def _fetch_concrete_density(self, db: AsyncSession) -> Optional[float]:
        """
        Look up the density of concrete (t/m3) from v_densities_detailed_level.
        Used as the tonnage conversion for the A4 transport calculation.
        Emissions Source = 'Concrete production process' → 2.4 t/m3.
        """
        result = await db.execute(
            text("""
                SELECT "Density"
                FROM v_densities_detailed_level
                WHERE "Emissions Source" = 'Concrete production process'
                  AND ("Jurisdiction" = :jur OR "Jurisdiction" = 'Global')
                ORDER BY
                    CASE WHEN "Jurisdiction" = :jur THEN 0 ELSE 1 END
                LIMIT 1
            """),
            {"jur": _JURISDICTION},
        )
        row = result.fetchone()
        return self._f(row._mapping["Density"]) if row else None

    async def _fetch_production_stage_ef(
        self,
        db: AsyncSession,
        dataset_revision_id: Optional[UUID] = None,
    ) -> float:
        """
        Fetch production-stage EF from v_grade34_detailed_level.

        Excel equivalent:
          XLOOKUP(
            "Concrete production process",
            tbl_detailed_level[Emissions Source],
            tbl_detailed_level[Scope 3 Emissions Factor (tCO2e/UoM)],
            0
          )

        Returns tCO2e/m3 directly (no /1000 conversion).
        """
        has_dataset_revision_col = await self._grade34_has_dataset_revision_column(db)
        if has_dataset_revision_col and dataset_revision_id is not None:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = 'Concrete production process'
                      AND (
                        dataset_revision_id = CAST(:dataset_revision_id AS uuid)
                        OR dataset_revision_id IS NULL
                      )
                    ORDER BY
                        (dataset_revision_id = CAST(:dataset_revision_id AS uuid)) DESC,
                        dataset_revision_id DESC NULLS LAST
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "dataset_revision_id": str(dataset_revision_id)},
            )
        elif has_dataset_revision_col:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = 'Concrete production process'
                      AND dataset_revision_id IS NULL
                    LIMIT 1
                """),
                {"jur": _JURISDICTION},
            )
        else:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = 'Concrete production process'
                    LIMIT 1
                """),
                {"jur": _JURISDICTION},
            )
        row = result.fetchone()
        return self._f(row._mapping["emission_factor_scope3"]) if row else 0.0

    async def _fetch_transport_ef(
        self,
        db: AsyncSession,
        transport_mode: Optional[str],
        dataset_revision_id: Optional[UUID] = None,
    ) -> Optional[float]:
        if not transport_mode:
            return None
        has_dataset_revision_col = await self._grade34_has_dataset_revision_column(db)
        if has_dataset_revision_col and dataset_revision_id is not None:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :mode
                      AND (
                        dataset_revision_id = CAST(:dataset_revision_id AS uuid)
                        OR dataset_revision_id IS NULL
                      )
                    ORDER BY
                        (dataset_revision_id = CAST(:dataset_revision_id AS uuid)) DESC,
                        dataset_revision_id DESC NULLS LAST
                    LIMIT 1
                """),
                {
                    "jur": _JURISDICTION,
                    "mode": transport_mode,
                    "dataset_revision_id": str(dataset_revision_id),
                },
            )
        elif has_dataset_revision_col:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :mode
                      AND dataset_revision_id IS NULL
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "mode": transport_mode},
            )
        else:
            result = await db.execute(
                text("""
                    SELECT "emission_factor_scope3"
                    FROM v_grade34_detailed_level
                    WHERE "Jurisdiction"     = :jur
                      AND "Emissions Source" = :mode
                    LIMIT 1
                """),
                {"jur": _JURISDICTION, "mode": transport_mode},
            )
        row = result.fetchone()
        return self._f(row._mapping["emission_factor_scope3"]) if row else None

    # ── Per-row calculation ───────────────────────────────────────────────────

    async def _calculate_material_row(
        self,
        db: AsyncSession,
        mat: ConcreteMixMaterialInput,
        binder_total: float,
        scm_frac: Optional[float],
        dataset_revision_id: Optional[UUID],
    ) -> ConcreteMixMaterialResult:
        warnings: List[str] = []

        # Resolve DB source name and sub-category from config
        cfg = _MATERIAL_CONFIG.get(mat.material_name)
        if cfg:
            db_src, display_sub_cat, transport_sub_cat, em_cat = cfg
        else:
            db_src           = mat.material_name
            display_sub_cat  = "Concrete components"
            transport_sub_cat = "Concrete components"
            em_cat           = "Materials"
            warnings.append(
                f"Material '{mat.material_name}' not in _MATERIAL_CONFIG — "
                f"using material_name directly for EF lookup and defaulting "
                f"sub-category to 'Concrete components'."
            )

        scm_qty = self._scm_adjusted_qty(mat.material_name, mat.quantity_kg_m3, binder_total, scm_frac)

        # Component EF
        scope3_ef = await self._fetch_component_ef(db, db_src, dataset_revision_id)
        if scope3_ef is None:
            warnings.append(
                f"No Scope 3 EF found for Emissions Source='{db_src}' "
                f"(Jurisdiction='Australia'). Component EF defaulted to 0."
            )
        component_ef = (scope3_ef or 0.0) * scm_qty / 1000.0

        # Transport distances — skip entirely when transport_sub_cat is None
        if transport_sub_cat is None:
            td = None
        else:
            td = await self._fetch_transport_distances(db, transport_sub_cat, dataset_revision_id)
            if td is None:
                warnings.append(
                    f"No transport distances found for "
                    f"Emissions Sub-Category='{transport_sub_cat}' "
                    f"(Jurisdiction='Australia'). Transport EF defaulted to 0."
                )

        truck_mode = td.get("truck_transport_mode") if td else None
        rail_mode  = td.get("rail_transport_mode")  if td else None
        sea_mode   = td.get("sea_transport_mode")   if td else None
        truck_km   = self._f(td.get("truck_km"))    if td else None
        rail_km    = self._f(td.get("rail_km"))     if td else None
        sea_km     = self._f(td.get("sea_km"))      if td else None

        # Transport EFs
        truck_ef = await self._fetch_transport_ef(db, truck_mode, dataset_revision_id)
        rail_ef  = await self._fetch_transport_ef(db, rail_mode, dataset_revision_id)
        sea_ef   = await self._fetch_transport_ef(db, sea_mode, dataset_revision_id)

        transport_ef = (
            ((truck_km or 0.0) * (truck_ef or 0.0))
            + ((rail_km or 0.0) * (rail_ef or 0.0))
            + ((sea_km  or 0.0) * (sea_ef  or 0.0))
        ) * scm_qty / 1000.0

        total_ef = component_ef + transport_ef

        return ConcreteMixMaterialResult(
            emissions_category=em_cat,
            emissions_sub_category=display_sub_cat,
            material_name=mat.material_name,
            quantity_kg_m3=mat.quantity_kg_m3,
            quantity_scm_applied=round_result(scm_qty),
            scope3_ef=scope3_ef,
            component_ef_tco2e_m3=round_result(component_ef),
            truck_transport_mode=truck_mode,
            rail_transport_mode=rail_mode,
            shipping_transport_mode=sea_mode,
            truck_km=truck_km,
            rail_km=rail_km,
            shipping_km=sea_km,
            truck_ef=truck_ef,
            rail_ef=rail_ef,
            shipping_ef=sea_ef,
            transport_ef_tco2e_m3=round_result(transport_ef),
            total_ef_tco2e_m3=round_result(total_ef),
            data_warnings=warnings,
        )

    @staticmethod
    def _f(v) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


# ─────────────────────────────────────────────────────────────────────────────
# EPD Shortcut — user provides GWP A1-3 directly from an EPD document
# ─────────────────────────────────────────────────────────────────────────────

class ConcreteEPDShortcutRequest(BaseModel):
    """
    Input for the EPD Shortcut path.

    The user supplies a GWP Total (A1-3) value directly from a product EPD
    instead of entering individual component quantities.  The A4 transport
    stage is still calculated from the DB the same way as the detailed path.
    """

    project_id: UUID = Field(..., description="Project this mix belongs to")
    mix_id_label: str = Field(..., min_length=1, max_length=100)
    mix_type: str = Field(..., description="'Ready-mix' | 'Precast' | 'Shotcrete'")
    strength_mpa: int = Field(..., gt=0, description="Compressive strength in MPa")
    volume_m3: float = Field(..., gt=0, description="Volume of this mix used on project (m3)")
    gwp_a1a3_kgco2e_m3: float = Field(
        ..., ge=0,
        description="GWP Total A1-3 from EPD document (kgCO2e/m3)",
    )

    @field_validator("mix_type")
    @classmethod
    def validate_mix_type(cls, v: str) -> str:
        if v not in _MIX_TYPES:
            raise ValueError(f"mix_type must be one of {sorted(_MIX_TYPES)}")
        return v


class ConcreteEPDShortcutResponse(BaseModel):
    """
    Result for the EPD Shortcut path.

    A1-3 GWP comes directly from the EPD input value.
    A4 transport is calculated the same way as the detailed path.
    Total emissions = (gwp_a1a3 + a4_ef) × volume_m3.

    Note: BAU comparison fields are not included — pending DB table.
    """

    project_id: UUID
    mix_id_label: str
    mix_type: str
    strength_mpa: int
    volume_m3: float

    gwp_a1a3_kgco2e_m3: float = Field(description="GWP Total A1-3 as supplied from EPD (kgCO2e/m3)")
    gwp_a1a3_tco2e_m3: float = Field(description="= gwp_a1a3_kgco2e_m3 / 1000")

    # Transport Stage A4
    a4_sub_category: str
    a4_truck_transport_mode: Optional[str] = None
    a4_truck_km: Optional[float] = None
    a4_truck_ef: Optional[float] = None
    a4_tonnage_conversion: Optional[float] = None
    transport_a4_ef_tco2e_m3: float

    total_emissions_tco2e: float = Field(
        description="= (gwp_a1a3_tco2e_m3 + transport_a4_ef_tco2e_m3) × volume_m3"
    )

    data_warnings: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level calculator instance (mirrors grade1_asset_calculations pattern)
# ─────────────────────────────────────────────────────────────────────────────

calculator = ConcreteMixCalculator()


async def calculate_epd_shortcut(
    db: AsyncSession,
    request: ConcreteEPDShortcutRequest,
) -> ConcreteEPDShortcutResponse:
    """
    Separate calculation path for the EPD Shortcut.

    Delegates to ConcreteMixCalculator helpers for A4 transport.
    """
    warnings: List[str] = []
    calc = ConcreteMixCalculator()

    dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(
        db, request.project_id
    )
    if not dataset_revision_id:
        raise ValueError(
            f"Could not resolve dataset_revision_id for project {request.project_id}. "
            f"Ensure either ProjectDatasetRevision assignment exists or DEFAULT dataset revision is available."
        )

    gwp_a1a3_tco2e = round_result(request.gwp_a1a3_kgco2e_m3 / 1000.0)

    a4_sub_cat  = calc._a4_sub_category(request.mix_type)
    a4_td       = await calc._fetch_transport_distances(db, a4_sub_cat, dataset_revision_id)
    if a4_td is None:
        warnings.append(
            f"No A4 transport distances found for sub-category='{a4_sub_cat}'. "
            f"A4 transport EF defaulted to 0."
        )
    a4_truck_mode = a4_td.get("truck_transport_mode") if a4_td else None
    a4_truck_km   = calc._f(a4_td.get("truck_km"))    if a4_td else None
    a4_truck_ef   = await calc._fetch_transport_ef(db, a4_truck_mode, dataset_revision_id)
    a4_density    = await calc._fetch_concrete_density(db)
    if a4_density is None:
        warnings.append(
            "Concrete density not found in v_densities_detailed_level. "
            "A4 transport EF defaulted to 0."
        )
    a4_ef = round_result(
        (a4_truck_km or 0.0) * (a4_truck_ef or 0.0) * (a4_density or 0.0)
    )

    # Keep A1-A3 fields as documented; include A4 only in total emissions.
    product_stage_total = round_result(gwp_a1a3_tco2e + a4_ef)
    total_em = round_result(product_stage_total * request.volume_m3)

    return ConcreteEPDShortcutResponse(
        project_id=request.project_id,
        mix_id_label=request.mix_id_label,
        mix_type=request.mix_type,
        strength_mpa=request.strength_mpa,
        volume_m3=request.volume_m3,
        gwp_a1a3_kgco2e_m3=request.gwp_a1a3_kgco2e_m3,
        gwp_a1a3_tco2e_m3=gwp_a1a3_tco2e,
        a4_sub_category=a4_sub_cat,
        a4_truck_transport_mode=a4_truck_mode,
        a4_truck_km=a4_truck_km,
        a4_truck_ef=a4_truck_ef,
        a4_tonnage_conversion=a4_density,
        transport_a4_ef_tco2e_m3=a4_ef,
        total_emissions_tco2e=total_em,
        data_warnings=warnings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Simplified Register — uses BAU default mix, adjusted for target SCM content
# ─────────────────────────────────────────────────────────────────────────────

class ConcreteSimplifiedRegisterRequest(BaseModel):
    """
    Input for the Simplified Register calculation path.

    The user supplies mix-level parameters only; component quantities are
    derived from the BAU default mix for the given strength grade, with
    binder quantities (GPC / Fly Ash / GGBF Slag) adjusted for the target
    SCM content.

    BAU SCM adjustment rules (differ from the detailed mix path):
      total_cementitious = GPC_bau + FA_bau + GGBF_bau   (from BAU table)
      default_max_fa_frac = FA_bau / total_cementitious
      GPC  = total_cementitious × (1 − scm_frac)
      FA   = total_cementitious × min(scm_frac, default_max_fa_frac)
      GGBF = total_cementitious × max(0, scm_frac − default_max_fa_frac)

    All other materials (aggregates, water, admixture) use BAU table values.

    BAU baseline (for comparison) uses the same mix but with 0% SCM
    (i.e. all cementitious content as GPC, no FA or GGBF).
    """

    project_id: UUID = Field(..., description="Project this mix belongs to")
    mix_type: str = Field(..., description="'Ready-mix' | 'Precast' | 'Shotcrete'")
    strength_mpa: int = Field(..., gt=0, description="Compressive strength in MPa")
    scm_pct: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Target SCM content as a percentage (0–100). "
            "Required — the simplified path always applies SCM adjustment."
        ),
    )
    volume_m3: float = Field(..., gt=0, description="Volume of this mix used on project (m3)")

    @field_validator("mix_type")
    @classmethod
    def validate_mix_type(cls, v: str) -> str:
        if v not in _MIX_TYPES:
            raise ValueError(f"mix_type must be one of {sorted(_MIX_TYPES)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "ad056efb-8f93-43cb-b750-bb622f6d48ea",
                "mix_type": "Ready-mix",
                "strength_mpa": 65,
                "scm_pct": 30,
                "volume_m3": 2,
            }
        }
    }


class ConcreteSimplifiedRegisterResponse(ConcreteMixCalculateResponse):
    """
    Result for the Simplified Register path.

    Extends ConcreteMixCalculateResponse with BAU baseline comparison fields.

    BAU baseline = same mix with 0% SCM (all cementitious as GPC, no FA/GGBF),
    using BAU default quantities for all other materials.

    BAU A1-3 EF is calculated using the same component + transport + production
    stage logic as the project mix, but with the 0% SCM quantities.

    Base case emissions = (bau_a1a3_tco2e_m3 + transport_a4_ef_tco2e_m3) × volume_m3
    NOTE: A4 EF is shared — the same concrete delivery transport applies to
    both the project mix and the BAU baseline.
    """

    bau_a1a3_tco2e_m3: float = Field(
        description=(
            "BAU Product Stage (A1-3) EF (tCO2e/m3) — "
            "calculated using the BAU default mix with 0% SCM (100% GPC baseline)."
        )
    )
    bau_a1a3_kgco2e_m3: float = Field(
        description="BAU A1-3 EF in kgCO2e/m3 = bau_a1a3_tco2e_m3 × 1000"
    )
    base_case_emissions_tco2e: float = Field(
        description=(
            "Base case emissions (tCO2e) = "
            "(bau_a1a3_tco2e_m3 + transport_a4_ef_tco2e_m3) × volume_m3"
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# Extend ConcreteMixCalculator with simplified-register methods
# ─────────────────────────────────────────────────────────────────────────────

# These methods are added here (after the class definition) by reopening the
# class to keep the simplified-register logic co-located with its models.

async def _calculate_simplified(
    self: "ConcreteMixCalculator",
    db: AsyncSession,
    request: ConcreteSimplifiedRegisterRequest,
) -> ConcreteSimplifiedRegisterResponse:
    """
    Simplified Register calculation — mirrors BAU Assumptions.xlsx formulas exactly.

    Excel formula mapping:
      total_cementitious  = XLOOKUP(strength, BAU!C126:J126, BAU!C128:J128)   ← BAU!C128
      bau_scm_frac        = XLOOKUP(strength, BAU!C126:J126, BAU!C124)         ← BAU!C124
      GPC                 = (1 - scm_frac) × total_cementitious
      FA                  = IF(scm < bau_scm, total_cem×scm, bau_scm×total_cem)
                          = total_cementitious × min(scm_frac, bau_scm_frac)
      GGBF                = IF(scm > bau_scm, (scm-bau_scm)×total_cem, 0)
                          = total_cementitious × max(0, scm_frac - bau_scm_frac)
      Other materials     = XLOOKUP(strength, BAU!C126:J126, BAU!C132:J139)   (unchanged)

    The derived material list is then fed into the same A1/A2/A3/A4 calculations
    as the detailed mix register (via self.calculate with scm_pct=None).
    Transport distances are looked up by Emissions Sub-Category (per _MATERIAL_CONFIG),
    not hardcoded — matching the Excel's XLOOKUP on tbl_transport_distances.
    """
    warnings: List[str] = []

    dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(
        db, request.project_id
    )
    if not dataset_revision_id:
        raise ValueError(
            f"Could not resolve dataset_revision_id for project {request.project_id}. "
            f"Ensure either ProjectDatasetRevision assignment exists or DEFAULT dataset revision is available."
        )

    # ── 1. Look up BAU grade data from v_bau_default_concrete_mix ───────────
    bau = await self._fetch_bau_grade_data(
        db,
        request.strength_mpa,
        dataset_revision_id=str(dataset_revision_id),
    )
    if bau is None:
        raise ValueError(
            f"No BAU default mix is defined for strength_mpa={request.strength_mpa}. "
            f"Check that concrete_mix_designs contains rows for this grade "
            f"and that concrete_mix_assumptions has an active row."
        )

    total_cementitious: float = bau["total_cementitious"]   # BAU Assumptions!C128
    bau_scm_frac: float       = bau["bau_scm_frac"]         # BAU Assumptions!C124
    scm_frac: float           = request.scm_pct / 100.0

    # ── 2. Compute cementitious quantities from BAU Assumptions formulas ──
    #   GPC  = (1 − scm_frac) × total_cementitious
    #   FA   = min(scm_frac, bau_scm_frac) × total_cementitious
    #   GGBF = max(0, scm_frac − bau_scm_frac) × total_cementitious
    gpc_qty  = total_cementitious * (1.0 - scm_frac)
    fa_qty   = total_cementitious * min(scm_frac, bau_scm_frac)
    ggbf_qty = total_cementitious * max(0.0, scm_frac - bau_scm_frac)

    # ── 3. Build the full material list ───────────────────────────────────
    # Cementitious materials computed above; non-cementitious taken directly from BAU table.
    # All rows are included even when qty=0 so every BAU material appears in material_breakdown.
    cementitious_rows: List[ConcreteMixMaterialInput] = [
        ConcreteMixMaterialInput(material_name="General Purpose Cement", quantity_kg_m3=gpc_qty),
        ConcreteMixMaterialInput(material_name="Fly Ash",                quantity_kg_m3=fa_qty),
        ConcreteMixMaterialInput(material_name="GGBF slag",              quantity_kg_m3=ggbf_qty),
    ]

    non_cementitious_rows: List[ConcreteMixMaterialInput] = [
        ConcreteMixMaterialInput(material_name=name, quantity_kg_m3=qty)
        for name, qty in bau["materials"]
    ]

    project_materials = cementitious_rows + non_cementitious_rows

    # ── 4. Calculate project mix (same A1/A2/A3/A4 logic as detailed register) ──
    calc_label = f"Simplified {request.mix_type} {request.strength_mpa}MPa"
    proj_req = ConcreteMixCalculateRequest(
        project_id=request.project_id,
        mix_id_label=calc_label,
        mix_type=request.mix_type,
        strength_mpa=request.strength_mpa,
        scm_pct=None,          # quantities already computed — no SCM adjustment in calculate()
        volume_m3=request.volume_m3,
        materials=project_materials,
    )
    proj_result = await self.calculate(db, proj_req)
    warnings.extend(proj_result.data_warnings)

    # ── 5. BAU baseline: 0% SCM — all cementitious as GPC, no FA or GGBF ─
    bau_baseline_materials: List[ConcreteMixMaterialInput] = [
        ConcreteMixMaterialInput(
            material_name="General Purpose Cement",
            quantity_kg_m3=total_cementitious,   # 100% GPC
        )
    ] + [
        ConcreteMixMaterialInput(material_name=name, quantity_kg_m3=qty)
        for name, qty in bau["materials"]
        if qty > 0
    ]

    bau_req = ConcreteMixCalculateRequest(
        project_id=request.project_id,
        mix_id_label="BAU-0pct-SCM",
        mix_type=request.mix_type,
        strength_mpa=request.strength_mpa,
        scm_pct=None,
        volume_m3=request.volume_m3,
        materials=bau_baseline_materials,
    )
    bau_result = await self.calculate(db, bau_req)

    bau_a1a3 = bau_result.gwp_a1a3_tco2e_m3
    bau_a1a3_kg = round_result(bau_a1a3 * 1000.0)
    # A4 EF is the same for both project and BAU (same mix_type → same sub-category)
    base_case_em = round_result(
        (bau_a1a3 + proj_result.transport_a4_ef_tco2e_m3) * request.volume_m3
    )

    # ── 6. Build response ─────────────────────────────────────────────────
    # Merge all warnings (BAU warnings are advisory; surface project-mix warnings)
    all_warnings = warnings[:]
    for w in bau_result.data_warnings:
        advisory = f"[BAU baseline] {w}"
        if advisory not in all_warnings:
            all_warnings.append(advisory)

    return ConcreteSimplifiedRegisterResponse(
        # Echo project_id and mix header (no user-supplied mix_id_label)
        project_id=request.project_id,
        mix_id_label=calc_label,
        mix_type=request.mix_type,
        strength_mpa=request.strength_mpa,
        scm_pct=request.scm_pct,
        volume_m3=request.volume_m3,
        # Stage-level EFs
        component_stage_ef_tco2e_m3=proj_result.component_stage_ef_tco2e_m3,
        transport_stage_ef_tco2e_m3=proj_result.transport_stage_ef_tco2e_m3,
        production_stage_ef_tco2e_m3=proj_result.production_stage_ef_tco2e_m3,
        gwp_a1a3_tco2e_m3=proj_result.gwp_a1a3_tco2e_m3,
        gwp_a1a3_kgco2e_m3=proj_result.gwp_a1a3_kgco2e_m3,
        # A4 transport
        a4_sub_category=proj_result.a4_sub_category,
        a4_truck_transport_mode=proj_result.a4_truck_transport_mode,
        a4_truck_km=proj_result.a4_truck_km,
        a4_truck_ef=proj_result.a4_truck_ef,
        a4_tonnage_conversion=proj_result.a4_tonnage_conversion,
        transport_a4_ef_tco2e_m3=proj_result.transport_a4_ef_tco2e_m3,
        # Totals
        total_emissions_tco2e=proj_result.total_emissions_tco2e,
        ef_label=proj_result.ef_label,
        material_breakdown=proj_result.material_breakdown,
        # BAU comparison
        bau_a1a3_tco2e_m3=bau_a1a3,
        bau_a1a3_kgco2e_m3=bau_a1a3_kg,
        base_case_emissions_tco2e=base_case_em,
        data_warnings=all_warnings,
    )


async def _get_default_dataset_revision_id(
    self: "ConcreteMixCalculator",
    db: AsyncSession,
) -> Optional[str]:
    """
    Fetch the published DEFAULT dataset revision ID from dataset_revisions.

    Returns:
        UUID string of the published DEFAULT revision, or None if not found.
    """
    result = await db.execute(
        text("""
            SELECT id
            FROM dataset_revisions
            WHERE scope_type = 'DEFAULT'
              AND status = 'published'
            ORDER BY created_at DESC
            LIMIT 1
        """)
    )
    row = result.fetchone()
    return str(row._mapping["id"]) if row else None


async def _fetch_bau_grade_data(
    self: "ConcreteMixCalculator",
    db: AsyncSession,
    strength_mpa: int,
    dataset_revision_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Query v_bau_default_concrete_mix for one strength grade and return a
    structured dict matching the shape expected by _calculate_simplified:

        {
            "total_cementitious": float,       # from is_total_cementitious row
            "bau_scm_frac":       float,       # default_max_fly_ash_pct (FA cap)
            "materials": [                     # non-cementitious rows only
                (component_label, quantity_kg_m3),
                ...
            ],
        }

    Args:
        strength_mpa:        compressive strength grade to look up.
        dataset_revision_id: UUID string of the user-created dataset revision to
                             use, or None (default) to fetch and use the platform
                             default (scope_type='DEFAULT').

    Returns None if no rows are found (grade not in concrete_mix_designs, or the
    requested revision does not exist / is not active).

    GPC / FA / GGBF quantities are NOT stored in the DB — they are always
    computed from total_cementitious + scm formulas in _calculate_simplified.
    """
    # If no specific revision supplied, fetch the DEFAULT dataset revision
    if dataset_revision_id is None:
        dataset_revision_id = await self._get_default_dataset_revision_id(db)
        if dataset_revision_id is None:
            return None
    
    result = await db.execute(
        text("""
            SELECT
                component_code,
                component_label,
                quantity_kg_m3,
                is_total_cementitious,
                default_max_fly_ash_pct
            FROM v_bau_default_concrete_mix
            WHERE dataset_revision_id = CAST(:rev_id AS uuid)
              AND strength_mpa = :grade
            ORDER BY display_order
        """),
        {"rev_id": dataset_revision_id, "grade": strength_mpa},
    )
    rows = result.fetchall()
    if not rows:
        return None

    total_cementitious: Optional[float] = None
    bau_scm_frac: Optional[float] = None
    materials: list[tuple[str, float]] = []

    for row in rows:
        m = row._mapping
        if m["is_total_cementitious"]:
            tc_raw  = m["quantity_kg_m3"]
            scm_raw = m["default_max_fly_ash_pct"]
            total_cementitious = float(tc_raw)  if tc_raw  is not None else None
            bau_scm_frac       = float(scm_raw) if scm_raw is not None else None
        else:
            # Keep only non-cementitious rows; GPC/FA/GGBF are derived from
            # the SCM formulas and must not be duplicated from BAU rows.
            if m["component_code"] in _BAU_BINDER_COMPONENT_CODES:
                continue
            qty_raw = m["quantity_kg_m3"]
            materials.append((m["component_label"], float(qty_raw) if qty_raw is not None else 0.0))

    if total_cementitious is None or bau_scm_frac is None:
        return None

    return {
        "total_cementitious": total_cementitious,
        "bau_scm_frac":       bau_scm_frac,
        "materials":          materials,
    }


# Attach methods to ConcreteMixCalculator without subclassing
ConcreteMixCalculator.calculate_simplified = _calculate_simplified
ConcreteMixCalculator._fetch_bau_grade_data = _fetch_bau_grade_data
ConcreteMixCalculator._get_default_dataset_revision_id = _get_default_dataset_revision_id


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience function for the simplified register
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_simplified_register(
    db: AsyncSession,
    request: ConcreteSimplifiedRegisterRequest,
) -> ConcreteSimplifiedRegisterResponse:
    """Entry point for the simplified register calculation (mirrors EPD shortcut pattern)."""
    return await calculator.calculate_simplified(db, request)

