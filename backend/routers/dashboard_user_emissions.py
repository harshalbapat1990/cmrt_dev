"""
routers/dashboard_user_emissions.py

Dashboard Results API — User Emissions (B8) Datagrid

Returns structured datagrid data for user emissions (road + rail) for all
project options in a stage instance.

  GET /api/dashboard/user-emissions
      project_id        UUID  required
      stage_instance_id UUID  required

Road emissions are sourced from emissions_results, keyed by project option,
assessment year, and vehicle type. Specialist user_emissions_* tables continue
to supply annual intensity and calculation detail. Activity_data supplies VKT,
speed, and rail inputs.

Rail data source (from activity_data):
  Small (NZ or AUS) / NZ Large → ui_table_key = 'railUsers'
  AUS Large                    → ui_table_key = 'largeRailUsers'

Grid row order follows the Excel reference CSV format:
  old/nz_roads_useremissions_excel.csv
  user_emissions_misc/Australian Example - Small projects.csv

Summary fields per option:
  interim_absolute_tco2e       = SUM(total_annual_emissions_tco2e) over all years
  base_case_interim_tco2e      = same for the base-case option
  final_user_emissions_tco2e   = option interim − base-case interim
  relative_road_emissions_tco2e (per-year row) = option annual total − base-case annual total
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from services._calc_utils import DashboardBase, round_decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_principal, Principal
from core.session import get_session

router = APIRouter(
    prefix="/api/dashboard/user-emissions",
    tags=["Dashboard - User Emissions (B8)"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dec(v) -> Optional[Decimal]:
    """Safely convert a value to Decimal; returns None on failure."""
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _normalize_key(label: str) -> str:
    """'General Fleet' → 'general_fleet', 'Super heavy vehicle' → 'super_heavy_vehicle'"""
    return label.lower().replace(" ", "_")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class UserEmissionsGridRow(DashboardBase):
    """One metric row in the road user emissions datagrid."""
    row_key: str             # e.g. "general_fleet_vkt"
    label: str               # Display label, e.g. "General Fleet (VKT)"
    row_type: str            # "input" | "calculated" | "total" | "relative"
    unit: str                # "VKT" | "km/h" | "gCO2e/km" | "tCO2e"
    values: List[Optional[Decimal]]  # One per year (index matches years list)


class UserEmissionsRoadSection(DashboardBase):
    """Road user emissions grid for one project option."""
    years: List[int]
    rows: List[UserEmissionsGridRow]
    interim_absolute_tco2e: Decimal
    base_case_interim_tco2e: Decimal
    final_user_emissions_tco2e: Decimal


class UserEmissionsRailSection(DashboardBase):
    """Rail user emissions for one project option (grid format matching road section)."""
    years: List[int]
    rows: List[UserEmissionsGridRow]   # GTK, diesel, emissions, absolute, relative train, relative road+rail
    total_annual_tco2e: Decimal        # scalar option total (all trains)
    base_case_annual_tco2e: Decimal    # scalar base-case total
    relative_annual_tco2e: Decimal     # option − base_case (scalar)


class UserEmissionsOptionResult(DashboardBase):
    """Road + rail user emissions for one project option."""
    option_id: UUID
    option_label: str
    is_base_case: bool
    road_section: Optional[UserEmissionsRoadSection] = None
    rail_section: Optional[UserEmissionsRailSection] = None


class UserEmissionsDashboardResponse(DashboardBase):
    project_id: UUID
    stage_instance_id: UUID
    project_class: str   # "SMALL" | "LARGE"
    jurisdiction: str    # "New Zealand" | state/country name
    is_nz: bool
    is_large: bool
    options: List[UserEmissionsOptionResult]


# ---------------------------------------------------------------------------
# SQL — project context
# ---------------------------------------------------------------------------

_PROJECT_CONTEXT_SQL = text("""
    SELECT
        p.project_class::text                AS project_class,
        COALESCE(p.operational_life_years, 1) AS operational_life_years,
        COALESCE(j.name, '')                 AS jurisdiction_name
    FROM   project p
    JOIN   organization  o ON o.id = p.proponent_org_id
    LEFT   JOIN jurisdictions j ON j.id = o.jurisdiction_id
    WHERE  p.id = CAST(:project_id AS uuid)
""")

# ---------------------------------------------------------------------------
# SQL — options
# ---------------------------------------------------------------------------

_OPTIONS_SQL = text("""
    SELECT id::text AS id, label, is_default
    FROM   project_options
    WHERE  stage_instance_id = CAST(:stage_id AS uuid)
    ORDER  BY option_number, created_at
""")

# ---------------------------------------------------------------------------
# SQL — NZ small road results
# ---------------------------------------------------------------------------

_NZ_SMALL_ROAD_SQL = text("""
    SELECT
        r.assessment_year,
        general_fleet_intensity_gco2e_km,
        light_vehicle_intensity_gco2e_km,
        heavy_vehicle_intensity_gco2e_km,
        bus_intensity_gco2e_km,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_general_fleet') AS general_fleet_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_light_vehicle') AS light_vehicle_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_heavy_vehicle') AS heavy_vehicle_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_bus') AS bus_emissions_tco2e,
        (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key ~ '^b8_road_') AS total_annual_emissions_tco2e
    FROM   user_emissions_nz_results r
    WHERE  r.project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  r.project_option_id         = CAST(:option_id AS uuid)
    ORDER  BY r.assessment_year
""")

# ---------------------------------------------------------------------------
# SQL — AUS small road results
# ---------------------------------------------------------------------------

_AUS_SMALL_ROAD_SQL = text("""
    SELECT
        r.assessment_year,
        light_vehicle_intensity_gco2e_km,
        medium_vehicle_intensity_gco2e_km,
        heavy_vehicle_intensity_gco2e_km,
        super_heavy_vehicle_intensity_gco2e_km,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_light_vehicle') AS light_vehicle_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_medium_vehicle') AS medium_vehicle_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_heavy_vehicle') AS heavy_vehicle_emissions_tco2e,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_super_heavy_vehicle') AS super_heavy_vehicle_emissions_tco2e,
        (SELECT COALESCE(SUM(er.value), 0) FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key ~ '^b8_road_') AS total_annual_emissions_tco2e
    FROM   user_emissions_aus_small_results r
    WHERE  r.project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  r.project_option_id         = CAST(:option_id AS uuid)
    ORDER  BY r.assessment_year
""")

# ---------------------------------------------------------------------------
# SQL — NZ large road results
# ---------------------------------------------------------------------------

_NZ_LARGE_ROAD_SQL = text("""
    SELECT
        r.assessment_year,
        r.vehicle_type,
        vkt_calc,
        speed_kph_calc,
        emissions_intensity_gco2e_km  AS emissions_intensity,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_' || regexp_replace(lower(r.vehicle_type), '[^a-z0-9]+', '_', 'g')) AS emissions_tco2e
    FROM   user_emissions_nz_large_road_results r
    WHERE  r.project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  r.project_option_id         = CAST(:option_id AS uuid)
    ORDER  BY r.vehicle_type, r.assessment_year
""")

# ---------------------------------------------------------------------------
# SQL — AUS large road results
# ---------------------------------------------------------------------------

_AUS_LARGE_ROAD_SQL = text("""
    SELECT
        r.assessment_year,
        r.vehicle_type,
        vkt_calc,
        speed_kph_calc,
        emissions_intensity_gco2e_vkt AS emissions_intensity,
        (SELECT er.value FROM emissions_results er WHERE er.project_option_id = r.project_option_id AND er.assessment_year = r.assessment_year AND er.value_key = 'b8_road_' || regexp_replace(lower(r.vehicle_type), '[^a-z0-9]+', '_', 'g')) AS emissions_tco2e
    FROM   user_emissions_aus_large_road_results r
    WHERE  r.project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  r.project_option_id         = CAST(:option_id AS uuid)
    ORDER  BY r.vehicle_type, r.assessment_year
""")

# ---------------------------------------------------------------------------
# SQL — road inputs from activity_data (small projects only)
# ---------------------------------------------------------------------------

_ROAD_INPUTS_SQL = text("""
    SELECT
        extra_fields->>'vehicle_type' AS vehicle_type,
        extra_fields->>'vkt'          AS vkt,
        extra_fields->>'avg_speed'    AS avg_speed,
        extra_fields->>'vht'          AS vht
    FROM   activity_data
    WHERE  project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  project_option_id         = CAST(:option_id AS uuid)
      AND  (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND  ui_table_key              = 'roadUsers'
      AND  extra_fields->>'vehicle_type' IS NOT NULL
""")

# ---------------------------------------------------------------------------
# SQL — rail data from activity_data (train_type, terrain, GTK only)
# ---------------------------------------------------------------------------

_RAIL_ACTIVITY_SQL = text("""
    SELECT
        id::text AS activity_data_id,
        extra_fields->>'vehicle_type' AS train_type,
        extra_fields->>'terrain'      AS terrain,
        extra_fields->>'freight'      AS gtk_value
    FROM   activity_data
    WHERE  project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  project_option_id         = CAST(:option_id AS uuid)
      AND  (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND  ui_table_key              IN ('railUsers', 'largeRailUsers')
      AND  extra_fields->>'vehicle_type' IS NOT NULL
    ORDER  BY created_at
""")

_RAIL_LEDGER_SQL = text("""
    SELECT ad.id::text AS activity_data_id, er.assessment_year,
           SUM(er.value) AS emissions_annual
    FROM emissions_results er
    JOIN activity_data ad
      ON er.value_key = 'b8_rail_' || replace(ad.id::text, '-', '') || '_' || er.assessment_year::text
    WHERE er.project_stage_instance_id = CAST(:stage_id AS uuid)
      AND ad.id = ANY(CAST(:activity_ids AS uuid[]))
      AND er.assessment_year IS NOT NULL
      AND er.lifecycle_module_code = 'B8'
      AND er.is_supplementary IS FALSE
      AND er.reporting_measure = 'actual'
    GROUP BY ad.id, er.assessment_year
""")

# ---------------------------------------------------------------------------
# SQL — freight rail factors (published revision)
# ---------------------------------------------------------------------------

_FREIGHT_RAIL_FACTORS_SQL = text("""
    SELECT frf.train_type, frf.terrain, frf.fuel_consumption_l_per_000_gtk
    FROM   freight_rail_factors frf
    JOIN   dataset_revisions dr ON dr.id = frf.dataset_revision_id
    WHERE  dr.status = 'published'
""")

# ---------------------------------------------------------------------------
# SQL — vehicle types from activity_data (large road projects)
# ---------------------------------------------------------------------------

_LARGE_ROAD_VTYPES_SQL = text("""
    SELECT DISTINCT extra_fields->>'vehicle_type' AS vehicle_type
    FROM   activity_data
    WHERE  project_stage_instance_id = CAST(:stage_id AS uuid)
      AND  project_option_id         = CAST(:option_id AS uuid)
      AND  (CAST(:submission_period_id AS uuid) IS NULL OR submission_period_id = CAST(:submission_period_id AS uuid))
      AND  ui_table_key              = :activity_key
      AND  extra_fields->>'vehicle_type' IS NOT NULL
""")


# ---------------------------------------------------------------------------
# Grid builders
# ---------------------------------------------------------------------------

def _build_small_road_grid(
    db_rows: list,
    vkt_map: Dict[str, Optional[Decimal]],
    speed_map: Dict[str, Optional[Decimal]],
    vehicle_types: List[tuple],           # [(normalized_key, display_label), ...]
    intensity_col_map: Dict[str, str],    # normalized_key → db column name
    emissions_col_map: Dict[str, str],    # normalized_key → db column name
    years: List[int],
    base_case_totals: Dict[int, Optional[Decimal]],  # year → base-case total
) -> List[UserEmissionsGridRow]:
    """
    Build an ordered list of grid rows for a small-project option (NZ or AUS).

    Row order:
      1. VKT rows          (one per vehicle type, constant across years)
      2. Speed rows         (one per vehicle type, constant across years)
      3. Intensity rows     (one per vehicle type, per year from results table)
      4. Annual-emissions rows (one per vehicle type, per year)
      5. Absolute total row (total_annual_emissions_tco2e per year)
      6. Relative row       (option total − base-case total per year)
    """
    by_year: Dict[int, dict] = {r["assessment_year"]: r for r in db_rows}
    n = len(years)
    grid: List[UserEmissionsGridRow] = []

    # 1. VKT input rows (constant value repeated for all years)
    for key, label in vehicle_types:
        vkt = vkt_map.get(key)
        grid.append(UserEmissionsGridRow(
            row_key=f"{key}_vkt",
            label=f"{label} (VKT)",
            row_type="input",
            unit="VKT",
            values=[vkt] * n,
        ))

    # 2. Speed input rows (constant)
    for key, label in vehicle_types:
        speed = speed_map.get(key)
        grid.append(UserEmissionsGridRow(
            row_key=f"{key}_speed",
            label=f"{label} (average speed km/h)",
            row_type="input",
            unit="km/h",
            values=[speed] * n,
        ))

    # 3. Emissions intensity rows (per year)
    for key, label in vehicle_types:
        col = intensity_col_map.get(key)
        grid.append(UserEmissionsGridRow(
            row_key=f"{key}_intensity",
            label=f"{label} (emissions intensity gCO2e/km)",
            row_type="calculated",
            unit="gCO2e/km",
            values=[_dec(by_year[y][col]) if col and y in by_year else None for y in years],
        ))

    # 4. Annual emissions rows (per year)
    for key, label in vehicle_types:
        col = emissions_col_map.get(key)
        grid.append(UserEmissionsGridRow(
            row_key=f"{key}_emissions",
            label=f"{label} emissions (tCO2e)",
            row_type="calculated",
            unit="tCO2e",
            values=[_dec(by_year[y][col]) if col and y in by_year else None for y in years],
        ))

    # 5. Absolute total row
    total_values = [
        _dec(by_year[y]["total_annual_emissions_tco2e"]) if y in by_year else None
        for y in years
    ]
    grid.append(UserEmissionsGridRow(
        row_key="total_annual_emissions",
        label="Absolute emissions - all road vehicles (tCO2e)",
        row_type="total",
        unit="tCO2e",
        values=total_values,
    ))

    # 6. Relative row (option total − base-case total per year)
    def _relative(yr: int, opt_total: Optional[Decimal]) -> Optional[Decimal]:
        if opt_total is None:
            return None
        bc = base_case_totals.get(yr)
        return opt_total - (bc or Decimal("0"))

    grid.append(UserEmissionsGridRow(
        row_key="relative_road_vehicle_emissions",
        label="Relative road vehicle user emissions (B8) (tCO2e)",
        row_type="relative",
        unit="tCO2e",
        values=[_relative(y, tv) for y, tv in zip(years, total_values)],
    ))

    return grid


def _build_large_road_grid(
    db_rows: list,
    years: List[int],
    base_case_totals: Dict[int, Optional[Decimal]],
) -> List[UserEmissionsGridRow]:
    """
    Build grid rows for a large-project option (NZ or AUS large).

    db_rows columns: assessment_year, vehicle_type, vkt_calc, speed_kph_calc,
                     emissions_intensity, emissions_tco2e

    Row order:
      1. VKT rows (one per vehicle type, varies by year)
      2. Speed rows
      3. Emissions intensity rows
      4. Annual emissions rows
      5. Absolute total row (sum of all vehicle types per year)
      6. Relative row (option total − base-case total per year)
    """
    # Group by vehicle_type preserving first-seen order
    by_vtype: Dict[str, Dict[int, dict]] = defaultdict(dict)
    vtype_order: List[str] = []
    for r in db_rows:
        vt = r["vehicle_type"]
        if vt not in by_vtype:
            vtype_order.append(vt)
        by_vtype[vt][r["assessment_year"]] = r

    grid: List[UserEmissionsGridRow] = []

    # 1. VKT rows
    for vt in vtype_order:
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(vt)}_vkt",
            label=f"{vt} (VKT)",
            row_type="input",
            unit="VKT",
            values=[_dec(by_vtype[vt].get(y, {}).get("vkt_calc")) for y in years],
        ))

    # 2. Speed rows
    for vt in vtype_order:
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(vt)}_speed",
            label=f"{vt} (average speed km/h)",
            row_type="input",
            unit="km/h",
            values=[_dec(by_vtype[vt].get(y, {}).get("speed_kph_calc")) for y in years],
        ))

    # 3. Emissions intensity rows
    for vt in vtype_order:
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(vt)}_intensity",
            label=f"{vt} (emissions intensity gCO2e/km)",
            row_type="calculated",
            unit="gCO2e/km",
            values=[_dec(by_vtype[vt].get(y, {}).get("emissions_intensity")) for y in years],
        ))

    # 4. Annual emissions rows
    for vt in vtype_order:
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(vt)}_emissions",
            label=f"{vt} emissions (tCO2e)",
            row_type="calculated",
            unit="tCO2e",
            values=[_dec(by_vtype[vt].get(y, {}).get("emissions_tco2e")) for y in years],
        ))

    # 5. Absolute total row (sum of all vehicle types per year)
    def _year_total(yr: int) -> Optional[Decimal]:
        vals = [_dec(by_vtype[vt].get(yr, {}).get("emissions_tco2e")) for vt in vtype_order]
        non_null = [v for v in vals if v is not None]
        return sum(non_null) if non_null else None

    total_values = [_year_total(y) for y in years]
    grid.append(UserEmissionsGridRow(
        row_key="total_annual_emissions",
        label="Absolute emissions - all road vehicles (tCO2e)",
        row_type="total",
        unit="tCO2e",
        values=total_values,
    ))

    # 6. Relative row
    def _relative(yr: int, opt_total: Optional[Decimal]) -> Optional[Decimal]:
        if opt_total is None:
            return None
        bc = base_case_totals.get(yr)
        return opt_total - (bc or Decimal("0"))

    grid.append(UserEmissionsGridRow(
        row_key="relative_road_vehicle_emissions",
        label="Relative road vehicle user emissions (B8) (tCO2e)",
        row_type="relative",
        unit="tCO2e",
        values=[_relative(y, tv) for y, tv in zip(years, total_values)],
    ))

    return grid


def _build_rail_grid(
    rail_rows: list,
    frf_map: Dict[tuple, Decimal],
    emissions_by_activity_year: Dict[tuple, Decimal],
    years: List[int],
    base_case_rail_by_year: Dict[int, Decimal],
    road_relative_per_year: Dict[int, Decimal],
) -> tuple:
    """
    Build rail grid rows (year arrays, constants repeated across years).

    Row order:
      1. {train} (GTK)              – constant from activity_data
      2. {train} diesel (kL)        – calculated: fc × GTK / 1,000,000
      3. {train} emissions (tCO2e)  – read from the saved result ledger
      4. Absolute emissions - all trains (tCO2e)
      5. Relative train user emissions (B8) (tCO2e)
      6. Relative road & rail user emissions (B8) (tCO2e)

    Returns (rows, option_rail_annual_total).
    """
    n = len(years)
    grid: List[UserEmissionsGridRow] = []

    # Per-train calculations
    rail_by_type: Dict[str, tuple] = {}   # train_type → (gtk, fuel_kl, annual values by year)
    train_order: List[str] = []
    for r in rail_rows:
        tt = r["train_type"] or ""
        if tt not in rail_by_type:
            train_order.append(tt)
        ter = (r["terrain"] or "").lower()
        gtk = _dec(r["gtk_value"]) or Decimal("0")
        fc = frf_map.get((tt.lower(), ter), Decimal("0"))
        fuel_kl = fc * gtk / Decimal("1000000")
        annual_values = {
            year: emissions_by_activity_year.get((str(r["activity_data_id"]), year), Decimal("0"))
            for year in years
        }
        rail_by_type[tt] = (gtk, fuel_kl, annual_values)

    # 1. GTK rows
    for tt in train_order:
        gtk, _, _ = rail_by_type[tt]
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(tt)}_gtk",
            label=f"{tt} (GTK)",
            row_type="input",
            unit="GTK",
            values=[gtk] * n,
        ))

    # 2. Diesel (kL) rows
    for tt in train_order:
        _, fuel_kl, _ = rail_by_type[tt]
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(tt)}_diesel_kl",
            label=f"{tt} diesel (kL)",
            row_type="calculated",
            unit="kL",
            values=[fuel_kl] * n,
        ))

    # 3. Emissions (tCO2e) rows
    for tt in train_order:
        _, _, annual_values = rail_by_type[tt]
        grid.append(UserEmissionsGridRow(
            row_key=f"{_normalize_key(tt)}_emissions",
            label=f"{tt} emissions (tCO2e)",
            row_type="calculated",
            unit="tCO2e",
            values=[annual_values.get(year, Decimal("0")) for year in years],
        ))

    # 4. Absolute total
    annual_total_by_year = {
        year: sum((values[2].get(year, Decimal("0")) for values in rail_by_type.values()), Decimal("0"))
        for year in years
    }
    opt_rail_annual = annual_total_by_year.get(years[0], Decimal("0")) if years else Decimal("0")
    grid.append(UserEmissionsGridRow(
        row_key="total_annual_rail_emissions",
        label="Absolute emissions - all trains (tCO2e)",
        row_type="total",
        unit="tCO2e",
        values=[annual_total_by_year.get(year, Decimal("0")) for year in years],
    ))

    # 5. Relative train
    rel_rail_by_year = {
        year: annual_total_by_year.get(year, Decimal("0")) - base_case_rail_by_year.get(year, Decimal("0"))
        for year in years
    }
    rel_rail = rel_rail_by_year.get(years[0], Decimal("0")) if years else Decimal("0")
    grid.append(UserEmissionsGridRow(
        row_key="relative_train_emissions",
        label="Relative train user emissions (B8) (tCO2e)",
        row_type="relative",
        unit="tCO2e",
        values=[rel_rail_by_year.get(year, Decimal("0")) for year in years],
    ))

    # 6. Combined relative road & rail
    grid.append(UserEmissionsGridRow(
        row_key="relative_road_rail_emissions",
        label="Relative road & rail user emissions (B8) (tCO2e)",
        row_type="relative",
        unit="tCO2e",
        values=[
            road_relative_per_year.get(yr, Decimal("0")) + rel_rail_by_year.get(yr, Decimal("0"))
            for yr in years
        ],
    ))

    return grid, opt_rail_annual


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=UserEmissionsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="User Emissions (B8) datagrid",
    description=(
        "Returns road and rail user emissions datagrid data for all options in a "
        "project stage instance.\n\n"
        "Annual road emissions are sourced from emissions_results. Dedicated road result tables provide intensity and calculation detail. Rail emissions are also sourced from emissions_results, with activity_data providing train inputs.\n\n"
        "Each option section includes road rows (grid of year × metric), rail rows "
        "and summary totals (interim absolute, base-case, and relative user emissions)."
    ),
)
async def get_user_emissions_dashboard(
    project_id:           UUID = Query(..., description="Project UUID"),
    stage_instance_id:    UUID = Query(..., description="Stage instance UUID"),
    project_option_id:    Optional[UUID] = Query(None, description="Project option UUID (optional filter)"),
    submission_period_id: Optional[UUID] = Query(None, description="Submission period UUID (optional filter)"),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> UserEmissionsDashboardResponse:
    try:
        # ------------------------------------------------------------------
        # 1. Project context (jurisdiction + class)
        # ------------------------------------------------------------------
        ctx = (
            await db.execute(_PROJECT_CONTEXT_SQL, {"project_id": str(project_id)})
        ).mappings().first()

        if ctx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        project_class = (ctx["project_class"] or "SMALL").upper()
        jurisdiction_name = ctx["jurisdiction_name"] or ""
        is_nz = jurisdiction_name.lower() == "new zealand"
        is_large = project_class == "LARGE"

        # ------------------------------------------------------------------
        # 2. Freight rail factors provide the displayed fuel quantity. Emissions
        #    values themselves are read from emissions_results below.
        # ------------------------------------------------------------------
        frf_rows = (await db.execute(_FREIGHT_RAIL_FACTORS_SQL)).mappings().all()
        frf_map: Dict[tuple, Decimal] = {}
        for fr in frf_rows:
            key = (str(fr["train_type"]).lower(), str(fr["terrain"]).lower())
            frf_map[key] = Decimal(str(fr["fuel_consumption_l_per_000_gtk"]))

        # ------------------------------------------------------------------
        # 4. Options for this stage instance
        # ------------------------------------------------------------------
        opt_rows = (
            await db.execute(_OPTIONS_SQL, {"stage_id": str(stage_instance_id)})
        ).mappings().all()

        if not opt_rows:
            return UserEmissionsDashboardResponse(
                project_id=project_id,
                stage_instance_id=stage_instance_id,
                project_class=project_class,
                jurisdiction=jurisdiction_name,
                is_nz=is_nz,
                is_large=is_large,
                options=[],
            )

        if project_option_id:
            opt_rows = [o for o in opt_rows if str(o["id"]) == str(project_option_id)]
            if not opt_rows:
                return UserEmissionsDashboardResponse(
                    project_id=project_id,
                    stage_instance_id=stage_instance_id,
                    project_class=project_class,
                    jurisdiction=jurisdiction_name,
                    is_nz=is_nz,
                    is_large=is_large,
                    options=[],
                )
        spid = str(submission_period_id) if submission_period_id else None

        base_case_option_id: Optional[str] = next(
            (r["id"] for r in opt_rows if r["is_default"]), None
        )

        # ------------------------------------------------------------------
        # 5. Choose road SQL
        # ------------------------------------------------------------------
        if not is_large and is_nz:
            road_sql = _NZ_SMALL_ROAD_SQL
            road_type = "nz_small"
        elif not is_large and not is_nz:
            road_sql = _AUS_SMALL_ROAD_SQL
            road_type = "aus_small"
        elif is_large and is_nz:
            road_sql = _NZ_LARGE_ROAD_SQL
            road_type = "nz_large"
        else:
            road_sql = _AUS_LARGE_ROAD_SQL
            road_type = "aus_large"

        # ------------------------------------------------------------------
        # 4. Pass-1: fetch road data for every option; build per-year totals
        #    We need the base-case totals before we can compute the relative row,
        #    so we collect everything first then build the final grid in pass-2.
        # ------------------------------------------------------------------
        # option_id → List[DB rows]
        option_road_db: Dict[str, list] = {}
        # option_id → {year: total_annual_tco2e}
        option_year_totals: Dict[str, Dict[int, Optional[Decimal]]] = {}
        # option_id → interim (scalar sum over all years)
        option_road_interim: Dict[str, Decimal] = {}
        # option_id → road inputs from activity_data (small only)
        option_road_inputs: Dict[str, list] = {}

        for opt in opt_rows:
            opt_id = opt["id"]
            params = {"stage_id": str(stage_instance_id), "option_id": opt_id, "submission_period_id": spid}

            road_rows = list((await db.execute(road_sql, params)).mappings().all())
            # For large projects: restrict to vehicle types entered in activity_data
            if road_type in ("nz_large", "aus_large"):
                vt_params = {
                    "stage_id": str(stage_instance_id),
                    "option_id": opt_id,
                    "activity_key": "largeRoadUsers",
                    "submission_period_id": spid,
                }
                vt_rows = (
                    await db.execute(_LARGE_ROAD_VTYPES_SQL, vt_params)
                ).mappings().all()
                allowed_vtypes = {r["vehicle_type"] for r in vt_rows if r["vehicle_type"]}
                if allowed_vtypes:
                    road_rows = [r for r in road_rows if r.get("vehicle_type") in allowed_vtypes]
            option_road_db[opt_id] = road_rows

            if not road_rows:
                option_year_totals[opt_id] = {}
                option_road_interim[opt_id] = Decimal("0")
                option_road_inputs[opt_id] = []
                continue

            # Per-year totals
            if road_type in ("nz_small", "aus_small"):
                yr_totals = {
                    r["assessment_year"]: _dec(r["total_annual_emissions_tco2e"])
                    for r in road_rows
                }
            else:
                # large: sum emissions_tco2e across vehicle types for each year
                yr_totals: Dict[int, Optional[Decimal]] = defaultdict(lambda: None)
                for r in road_rows:
                    yr = r["assessment_year"]
                    val = _dec(r["emissions_tco2e"])
                    if val is not None:
                        yr_totals[yr] = (yr_totals[yr] or Decimal("0")) + val

            option_year_totals[opt_id] = dict(yr_totals)
            option_road_interim[opt_id] = sum(
                (v for v in yr_totals.values() if v is not None),
                Decimal("0"),
            )

            # Road inputs (small only)
            if road_type in ("nz_small", "aus_small"):
                input_rows = (await db.execute(_ROAD_INPUTS_SQL, params)).mappings().all()
                option_road_inputs[opt_id] = list(input_rows)
            else:
                option_road_inputs[opt_id] = []

        # Base-case per-year totals for the relative row
        base_case_year_totals: Dict[int, Optional[Decimal]] = (
            option_year_totals.get(base_case_option_id, {})
            if base_case_option_id else {}
        )
        base_case_road_interim = (
            option_road_interim.get(base_case_option_id, Decimal("0"))
            if base_case_option_id else Decimal("0")
        )

        # ------------------------------------------------------------------
        # 5. Pass-2: build final road grid per option
        # ------------------------------------------------------------------
        option_road_sections: Dict[str, Optional[UserEmissionsRoadSection]] = {}

        for opt in opt_rows:
            opt_id = opt["id"]
            road_rows = option_road_db[opt_id]

            if not road_rows:
                option_road_sections[opt_id] = None
                continue

            # Years list
            if road_type in ("nz_large", "aus_large"):
                years = sorted(set(r["assessment_year"] for r in road_rows))
            else:
                years = sorted(r["assessment_year"] for r in road_rows)

            # VKT / speed maps for small projects
            vkt_map: Dict[str, Optional[Decimal]] = {}
            speed_map: Dict[str, Optional[Decimal]] = {}
            if road_type in ("nz_small", "aus_small"):
                for ir in option_road_inputs[opt_id]:
                    vtype = ir["vehicle_type"] or ""
                    key = _normalize_key(vtype)
                    vkt_map[key] = _dec(ir["vkt"])
                    avg_speed = _dec(ir["avg_speed"])
                    # Fallback: derive speed from VKT ÷ VHT if avg_speed not stored
                    if avg_speed is None and ir["vht"]:
                        vkt_val = _dec(ir["vkt"])
                        vht_val = _dec(ir["vht"])
                        if vkt_val and vht_val and vht_val > 0:
                            avg_speed = round_decimal(vkt_val / vht_val)
                    speed_map[key] = avg_speed

            # Build grid rows
            if road_type == "nz_small":
                vehicle_types = [
                    ("general_fleet",  "General Fleet"),
                    ("light_vehicle",  "Light Vehicle"),
                    ("heavy_vehicle",  "Heavy Vehicle"),
                    ("bus",            "Bus"),
                ]
                intensity_col_map = {
                    "general_fleet": "general_fleet_intensity_gco2e_km",
                    "light_vehicle": "light_vehicle_intensity_gco2e_km",
                    "heavy_vehicle": "heavy_vehicle_intensity_gco2e_km",
                    "bus":           "bus_intensity_gco2e_km",
                }
                emissions_col_map = {
                    "general_fleet": "general_fleet_emissions_tco2e",
                    "light_vehicle": "light_vehicle_emissions_tco2e",
                    "heavy_vehicle": "heavy_vehicle_emissions_tco2e",
                    "bus":           "bus_emissions_tco2e",
                }
                grid_rows = _build_small_road_grid(
                    road_rows, vkt_map, speed_map,
                    vehicle_types, intensity_col_map, emissions_col_map,
                    years, base_case_year_totals,
                )

            elif road_type == "aus_small":
                vehicle_types = [
                    ("light_vehicle",       "Light vehicle"),
                    ("medium_vehicle",      "Medium vehicle"),
                    ("heavy_vehicle",       "Heavy vehicle"),
                    ("super_heavy_vehicle", "Super heavy vehicle"),
                ]
                intensity_col_map = {
                    "light_vehicle":       "light_vehicle_intensity_gco2e_km",
                    "medium_vehicle":      "medium_vehicle_intensity_gco2e_km",
                    "heavy_vehicle":       "heavy_vehicle_intensity_gco2e_km",
                    "super_heavy_vehicle": "super_heavy_vehicle_intensity_gco2e_km",
                }
                emissions_col_map = {
                    "light_vehicle":       "light_vehicle_emissions_tco2e",
                    "medium_vehicle":      "medium_vehicle_emissions_tco2e",
                    "heavy_vehicle":       "heavy_vehicle_emissions_tco2e",
                    "super_heavy_vehicle": "super_heavy_vehicle_emissions_tco2e",
                }
                grid_rows = _build_small_road_grid(
                    road_rows, vkt_map, speed_map,
                    vehicle_types, intensity_col_map, emissions_col_map,
                    years, base_case_year_totals,
                )

            else:
                # NZ large or AUS large
                grid_rows = _build_large_road_grid(
                    road_rows, years, base_case_year_totals
                )

            road_interim = option_road_interim[opt_id]
            option_road_sections[opt_id] = UserEmissionsRoadSection(
                years=years,
                rows=grid_rows,
                interim_absolute_tco2e=road_interim,
                base_case_interim_tco2e=base_case_road_interim,
                final_user_emissions_tco2e=road_interim - base_case_road_interim,
            )

        # ------------------------------------------------------------------
        # 6. Rail sections (grid format with year columns)
        # ------------------------------------------------------------------

        # 6a. Fetch rail activity data per option
        option_rail_db: Dict[str, list] = {}
        for opt in opt_rows:
            opt_id = opt["id"]
            params = {"stage_id": str(stage_instance_id), "option_id": opt_id, "submission_period_id": spid}
            rail_db_rows = (await db.execute(_RAIL_ACTIVITY_SQL, params)).mappings().all()
            option_rail_db[opt_id] = list(rail_db_rows)

        rail_activity_ids = [
            row["activity_data_id"]
            for rows in option_rail_db.values()
            for row in rows
        ]
        emissions_by_activity_year: Dict[tuple, Decimal] = {}
        if rail_activity_ids:
            ledger_rows = (await db.execute(
                _RAIL_LEDGER_SQL,
                {
                    "stage_id": str(stage_instance_id),
                    "activity_ids": [UUID(str(activity_id)) for activity_id in rail_activity_ids],
                },
            )).mappings().all()
            emissions_by_activity_year = {
                (str(row["activity_data_id"]), int(row["assessment_year"])):
                    (_dec(row["emissions_annual"]) or Decimal("0"))
                for row in ledger_rows
            }

        # 6b. Shared years list (from first road section that has data)
        all_years: List[int] = []
        for opt in opt_rows:
            rs = option_road_sections.get(opt["id"])
            if rs:
                all_years = rs.years
                break

        # Base-case rail annual totals are direct sums of saved annual ledger facts.
        base_case_rail_by_year: Dict[int, Decimal] = {year: Decimal("0") for year in all_years}
        if base_case_option_id and base_case_option_id in option_rail_db:
            for row in option_rail_db[base_case_option_id]:
                for year in all_years:
                    base_case_rail_by_year[year] += emissions_by_activity_year.get(
                        (str(row["activity_data_id"]), year), Decimal("0")
                    )
        base_case_rail_annual = base_case_rail_by_year.get(all_years[0], Decimal("0")) if all_years else Decimal("0")

        # 6c. Build rail grids per option
        option_rail_sections: Dict[str, Optional[UserEmissionsRailSection]] = {}
        for opt in opt_rows:
            opt_id = opt["id"]
            rail_rows = option_rail_db[opt_id]

            if not rail_rows or not all_years:
                option_rail_sections[opt_id] = None
                continue

            road_relative_per_year: Dict[int, Decimal] = {
                yr: (option_year_totals[opt_id].get(yr) or Decimal("0"))
                    - (base_case_year_totals.get(yr) or Decimal("0"))
                for yr in all_years
            }

            grid_rows, opt_rail_annual = _build_rail_grid(
                rail_rows=rail_rows,
                frf_map=frf_map,
                emissions_by_activity_year=emissions_by_activity_year,
                years=all_years,
                base_case_rail_by_year=base_case_rail_by_year,
                road_relative_per_year=road_relative_per_year,
            )

            option_rail_sections[opt_id] = UserEmissionsRailSection(
                years=all_years,
                rows=grid_rows,
                total_annual_tco2e=opt_rail_annual,
                base_case_annual_tco2e=base_case_rail_annual,
                relative_annual_tco2e=opt_rail_annual - base_case_rail_annual,
            )

        # ------------------------------------------------------------------
        # 7. Assemble response
        # ------------------------------------------------------------------
        options_result: List[UserEmissionsOptionResult] = []
        for opt in opt_rows:
            opt_id = opt["id"]
            is_base = bool(opt["is_default"])
            # Append "(Base case)" to label if this is the base case option
            option_label = f"{opt['label']} (Base case)" if is_base else opt["label"]
            options_result.append(UserEmissionsOptionResult(
                option_id=UUID(opt_id),
                option_label=option_label,
                is_base_case=is_base,
                road_section=option_road_sections.get(opt_id),
                rail_section=option_rail_sections.get(opt_id),
            ))

        return UserEmissionsDashboardResponse(
            project_id=project_id,
            stage_instance_id=stage_instance_id,
            project_class=project_class,
            jurisdiction=jurisdiction_name,
            is_nz=is_nz,
            is_large=is_large,
            options=options_result,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User emissions dashboard query failed: {exc}",
        )
