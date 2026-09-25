"""
services/user_emissions_aus_large_road_calculations.py

AUS large-project road user-emissions (B8) calculation service.

Excel sheet reference: "Australian Example - Large projects"

Large-project difference vs. small:
  - User supplies VKT + speed for SPECIFIC modelled years (anchor points).
  - All other reference-period years are interpolated or extrapolated.
  - User selects road parameters (gradient / curvature / roughness) explicitly.
  - All 20 ATAP vehicle classes are supported.

Interpolation / extrapolation (matching Excel formulas):
  Before first anchor : flat at first anchor (carry-back to commencement year)
  Between anchors     : piecewise linear interpolation
    Formula: v = v_a + (v_b - v_a) * (Y - y_a) / (y_b - y_a)
  After last anchor   : linear extrapolation using the same slope as the last
                        two anchors (FORECAST.LINEAR equivalent)

If only one anchor is supplied: flat value used for all years.

Emission intensity formula:
  emissions_tco2e = VKT × emissions_intensity_gco2e_vkt / 1,000,000

Road parameter text → numeric mappings (large-project values):
  gradient  (m/km)     : Flat=0, Moderate=40, Steep=60, Very steep=80
  curvature (deg/km)   : Straight=20, Gently curved=120, Very winding=300
  roughness → IRI(m/km): Very smooth=1.0, Smooth=2.0, Moderate=3.0, Rough=4.0, Very rough=5.0, Severely Rough=6.0
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

import uuid as _uuid

from sqlalchemy import func as sa_func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_emissions_aus_large_road import UserEmissionsAusLargeRoadResult
from schemas.user_emissions_aus_large_road import (
    AusLargeRoadAnnualRow,
    AusLargeRoadCalculateRequest,
    AusLargeRoadCalculateResponse,
    VehicleTypeAnnualResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Road parameter mappings (text → numeric for fn_veh_emissions_intensity_aus)
# ─────────────────────────────────────────────────────────────────────────────

# gradient in m/km — large-project descriptor set
_GRADIENT_MAP: dict[str, float] = {
    "Flat":       0.0,
    "Moderate":  40.0,
    "Steep":     60.0,
    "Very steep": 80.0,
}

# curvature in deg/km — large-project descriptor set
_CURVATURE_MAP: dict[str, float] = {
    "Straight":      20.0,
    "Gently curved": 120.0,
    "Very winding":  300.0,
}

# IRI (roughness) in m/km — 6-level large-project scale
_IRI_MAP: dict[str, float] = {
    "Very smooth":    1.0,
    "Smooth":         2.0,
    "Moderate":       3.0,
    "Rough":          4.0,
    "Very rough":     5.0,
    "Severely Rough": 6.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# Project reference period helper
# ─────────────────────────────────────────────────────────────────────────────

_AUS_INTENSITY_SQL = text("""
    SELECT vehicle_class, fleet_avg_emissions_intensity_gco2e_per_vkt
    FROM fn_veh_emissions_intensity_aus(
        :p_year, :p_state, :p_scenario,
        :p_gradient, :p_curvature, :p_iri,
        :p_speed_kph
    )
""")


# ─────────────────────────────────────────────────────────────────────────────
# Fetch base-case option and its interim emissions (ALL vehicle types)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_base_case_emissions(
    db: AsyncSession,
    project_stage_instance_id: UUID,
) -> tuple[UUID, Decimal]:
    """
    Finds the base-case option (is_default=true) for a given stage instance
    and returns (base_case_option_id, interim_emissions_tco2e).

    interim_emissions_tco2e is the SUM of emissions across ALL vehicle types
    stored in user_emissions_aus_large_road_results for that option.
    Returns 0 when the base case has not been calculated yet.
    """
    base_case_row = (
        await db.execute(
            text(
                "SELECT id FROM project_options "
                "WHERE stage_instance_id = :stage_id "
                "  AND is_default = true "
                "LIMIT 1"
            ),
            {"stage_id": str(project_stage_instance_id)},
        )
    ).mappings().first()

    if base_case_row is None:
        raise ValueError(
            f"No base-case option (is_default=true) found for stage instance "
            f"{project_stage_instance_id}. "
            "Please designate one option as the base case before calculating user emissions."
        )

    base_case_option_id = base_case_row["id"]

    interim_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_aus_large_road_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(base_case_option_id)},
        )
    ).mappings().first()

    interim_emissions = Decimal(interim_row["interim_total"]) if interim_row else Decimal("0")
    return base_case_option_id, interim_emissions



async def _get_project_reference_period(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, int, str]:
    """
    Returns (commencement_year, operational_life_years, state_name).
    state_name is from organization.region_id → jurisdictions.name (e.g. 'New South Wales').
    """
    row = (
        await db.execute(
            text(
                "SELECT EXTRACT(YEAR FROM p.commencement_of_operations)::int AS comm_year,"
                "       p.operational_life_years,"
                "       j.name AS state_name"
                "  FROM project p"
                "  JOIN organization o ON o.id = p.proponent_org_id"
                "  LEFT JOIN jurisdictions j ON j.id = o.region_id"
                " WHERE p.id = :pid"
            ),
            {"pid": str(project_id)},
        )
    ).mappings().first()

    if row is None:
        raise ValueError(f"Project {project_id} not found.")
    if row["comm_year"] is None:
        raise ValueError(
            "Project does not have a commencement_of_operations date set. "
            "Please set it before running the user-emissions calculation."
        )
    if row["operational_life_years"] is None:
        raise ValueError(
            "Project does not have an operational_life_years value set. "
            "Please set it before running the user-emissions calculation."
        )
    if row["state_name"] is None:
        raise ValueError(
            "The proponent organisation for this project does not have a region set. "
            "Please update the organisation's region before running the AUS calculation."
        )

    return int(row["comm_year"]), int(row["operational_life_years"]), row["state_name"]


# ─────────────────────────────────────────────────────────────────────────────
# Data-range clamp helper (same as AUS small — data only goes to 2050)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_aus_year_range(db: AsyncSession) -> tuple[int, int]:
    """Returns (min_year, max_year) across ev_uptake_factors and electric_decarb_factors."""
    row = (
        await db.execute(
            text(
                "SELECT LEAST("
                "    (SELECT MAX(year) FROM ev_uptake_factors),"
                "    (SELECT MAX(year) FROM electric_decarb_factors)"
                ") AS max_year,"
                "GREATEST("
                "    (SELECT MIN(year) FROM ev_uptake_factors),"
                "    (SELECT MIN(year) FROM electric_decarb_factors)"
                ") AS min_year"
            )
        )
    ).mappings().first()
    min_y = int(row["min_year"]) if row and row["min_year"] is not None else 2020
    max_y = int(row["max_year"]) if row and row["max_year"] is not None else 2050
    return min_y, max_y


# ─────────────────────────────────────────────────────────────────────────────
# Internal anchor type for interpolation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class _SimpleAnchor:
    year:              int
    vkt:               Decimal
    average_speed_kph: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# Interpolation / extrapolation
# ─────────────────────────────────────────────────────────────────────────────

def _build_year_values(
    anchors: list[_SimpleAnchor],
    ref_years: list[int],
) -> dict[int, tuple[Decimal, Decimal]]:
    """
    Returns {assessment_year: (vkt, speed_kph)} for every year in ref_years.

    Rules (matching Excel formulas):
      Y < first anchor  : use first anchor values (flat carry-back)
      first <= Y <= last: piecewise linear interpolation between consecutive anchors
      Y > last anchor   : linear extrapolation from the last two anchors
                          (FORECAST.LINEAR equivalent)
      Only one anchor   : flat value for all years
    """
    sorted_anchors = sorted(anchors, key=lambda a: a.year)
    result: dict[int, tuple[Decimal, Decimal]] = {}

    for Y in ref_years:
        if len(sorted_anchors) == 1 or Y <= sorted_anchors[0].year:
            # Flat carry-back (or single anchor)
            result[Y] = (sorted_anchors[0].vkt, sorted_anchors[0].average_speed_kph)

        elif Y >= sorted_anchors[-1].year:
            if len(sorted_anchors) >= 2:
                # Extrapolate from last two anchors
                a = sorted_anchors[-2]
                b = sorted_anchors[-1]
                dy = Decimal(str(b.year - a.year))
                t  = Decimal(str(Y - a.year)) / dy
                vkt   = a.vkt   + (b.vkt   - a.vkt)   * t
                speed = a.average_speed_kph + (b.average_speed_kph - a.average_speed_kph) * t
                result[Y] = (vkt, speed)
            else:
                result[Y] = (sorted_anchors[-1].vkt, sorted_anchors[-1].average_speed_kph)

        else:
            # Piecewise linear interpolation between consecutive anchors
            for i in range(len(sorted_anchors) - 1):
                a = sorted_anchors[i]
                b = sorted_anchors[i + 1]
                if a.year <= Y <= b.year:
                    dy = Decimal(str(b.year - a.year))
                    t  = Decimal(str(Y - a.year)) / dy
                    vkt   = a.vkt   + (b.vkt   - a.vkt)   * t
                    speed = a.average_speed_kph + (b.average_speed_kph - a.average_speed_kph) * t
                    result[Y] = (vkt, speed)
                    break

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main calculation entry point
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_and_store_aus_large_road(
    db: AsyncSession,
    req: AusLargeRoadCalculateRequest,
) -> AusLargeRoadCalculateResponse:
    """
    1. Resolve reference period (commencement year, operational life, state).
    2. Map text road parameters to numeric values for fn_veh_emissions_intensity_aus.
    3. For each vehicle type: interpolate / extrapolate VKT and speed for all
       reference-period years using that vehicle's anchor data.
    4. For each year: call fn_veh_emissions_intensity_aus once per unique speed
       (cached), look up intensity per vehicle type, compute emissions.
    5. Upsert UserEmissionsAusLargeRoadResult rows for all vehicle types.
    6. Return per-vehicle annual rows + interim total + final user emissions.

    The caller must commit the session after a successful return.
    """

    # ── 1. Reference period ──────────────────────────────────────────────────
    commencement_year, operational_life_years, state_name = (
        await _get_project_reference_period(db, req.project_id)
    )
    ref_years = list(range(commencement_year, commencement_year + operational_life_years))

    # ── 2. Road parameter mapping ────────────────────────────────────────────
    gradient_val  = _GRADIENT_MAP.get(req.gradient)
    curvature_val = _CURVATURE_MAP.get(req.curvature)
    iri_val       = _IRI_MAP.get(req.roughness)

    if gradient_val is None:
        raise ValueError(
            f"Unknown gradient '{req.gradient}'. "
            f"Valid values: {list(_GRADIENT_MAP.keys())}"
        )
    if curvature_val is None:
        raise ValueError(
            f"Unknown curvature '{req.curvature}'. "
            f"Valid values: {list(_CURVATURE_MAP.keys())}"
        )
    if iri_val is None:
        raise ValueError(
            f"Unknown roughness '{req.roughness}'. "
            f"Valid values: {list(_IRI_MAP.keys())}"
        )

    # ── 3. Data year clamp range ─────────────────────────────────────────────
    # Confirmed: retain flat values for post-2050 (James Addis, 2026-04-24)
    aus_min_year, aus_max_year = await _get_aus_year_range(db)

    # ── 4. Build per-vehicle anchor lists and interpolate for all years ──────
    # Collect anchors keyed by vehicle_type.
    # A vehicle type may not appear in every anchor year — that is valid as long
    # as it appears in at least one.
    vehicle_anchors: dict[str, list[_SimpleAnchor]] = {}
    for ay in req.anchor_years:
        for v in ay.vehicles:
            vehicle_anchors.setdefault(v.vehicle_type, []).append(
                _SimpleAnchor(
                    year=ay.year,
                    vkt=v.vkt,
                    average_speed_kph=v.average_speed_kph,
                )
            )

    # Interpolate/extrapolate for each vehicle type independently
    vehicle_year_values: dict[str, dict[int, tuple[Decimal, Decimal]]] = {
        vt: _build_year_values(anchors, ref_years)
        for vt, anchors in vehicle_anchors.items()
    }

    # ── 5. Loop over years and vehicle types; cache DB calls by (year, speed) ─
    # intensity_cache: (lookup_year, speed_float) → {vehicle_class: Optional[Decimal]}
    intensity_cache: dict[tuple[int, float], dict[str, Optional[Decimal]]] = {}

    vehicle_annual_rows: dict[str, list[AusLargeRoadAnnualRow]] = {
        vt: [] for vt in vehicle_anchors
    }

    t = UserEmissionsAusLargeRoadResult.__table__

    for year in ref_years:
        for vt, year_vals in vehicle_year_values.items():
            vkt, speed = year_vals[year]
            lookup_year = max(aus_min_year, min(aus_max_year, year))
            cache_key = (lookup_year, float(speed))

            # Only call fn_veh_emissions_intensity_aus once per (year, speed) combo
            if cache_key not in intensity_cache:
                rows = (
                    await db.execute(
                        _AUS_INTENSITY_SQL,
                        {
                            "p_year":      lookup_year,
                            "p_state":     state_name,
                            "p_scenario":  req.ev_uptake_scenario,
                            "p_gradient":  gradient_val,
                            "p_curvature": curvature_val,
                            "p_iri":       iri_val,
                            "p_speed_kph": float(speed),
                        },
                    )
                ).mappings().all()
                intensity_cache[cache_key] = {
                    r["vehicle_class"]: (
                        Decimal(str(r["fleet_avg_emissions_intensity_gco2e_per_vkt"]))
                        .quantize(Decimal("0.000001"))
                        if r["fleet_avg_emissions_intensity_gco2e_per_vkt"] is not None
                        else None
                    )
                    for r in rows
                }

            intensity: Optional[Decimal] = intensity_cache[cache_key].get(vt)

            # emissions_tco2e = VKT × gCO2e/km / 1,000,000
            emissions: Optional[Decimal] = None
            if intensity is not None:
                emissions = (vkt * intensity / Decimal("1000000")).quantize(Decimal("0.000001"))

            vkt_q   = vkt.quantize(Decimal("0.000001"))
            speed_q = speed.quantize(Decimal("0.0001"))

            vehicle_annual_rows[vt].append(
                AusLargeRoadAnnualRow(
                    assessment_year=year,
                    vkt_calc=vkt_q,
                    speed_kph_calc=speed_q,
                    emissions_intensity_gco2e_vkt=intensity,
                    emissions_tco2e=emissions,
                )
            )

            # Upsert into DB
            ins = pg_insert(UserEmissionsAusLargeRoadResult).values(
                id=_uuid.uuid4(),
                project_id=req.project_id,
                project_stage_instance_id=req.project_stage_instance_id,
                project_option_id=req.project_option_id,
                vehicle_type=vt,
                assessment_year=year,
                vkt_calc=vkt_q,
                speed_kph_calc=speed_q,
                gradient_m_per_km=Decimal(str(gradient_val)),
                curvature_deg_per_km=Decimal(str(curvature_val)),
                iri_m_per_km=Decimal(str(iri_val)),
                emissions_intensity_gco2e_vkt=intensity,
                emissions_tco2e=emissions,
            )
            await db.execute(
                ins.on_conflict_do_update(
                    constraint="uq_aus_large_road_option_vehicle_year",
                    set_={
                        "vkt_calc":                      ins.excluded.vkt_calc,
                        "speed_kph_calc":                ins.excluded.speed_kph_calc,
                        "gradient_m_per_km":             ins.excluded.gradient_m_per_km,
                        "curvature_deg_per_km":          ins.excluded.curvature_deg_per_km,
                        "iri_m_per_km":                  ins.excluded.iri_m_per_km,
                        "emissions_intensity_gco2e_vkt": ins.excluded.emissions_intensity_gco2e_vkt,
                        "emissions_tco2e":               ins.excluded.emissions_tco2e,
                        "created_at":                    sa_func.now(),
                    },
                )
            )

    # ── 6. Interim total: re-read from DB (all vehicle types for this option) ──
    # This mirrors the NZ/AUS-small pattern: after every vehicle-type call the
    # response shows the ACCUMULATED total for the option, not just this call.
    total_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_aus_large_road_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(req.project_option_id)},
        )
    ).mappings().first()
    interim_total_rounded = Decimal(str(total_row["interim_total"])).quantize(Decimal("0.000001"))

    # ── 7. Fetch base case and calculate final user emissions ────────────────
    # Rules (same as NZ/AUS-small, confirmed with James Addis):
    #   - Base case = is_default=true option in project_options.
    #   - interim_total for base case = SUM across ALL vehicle types in DB.
    #   - If base case has no results yet → treat as 0 → final = 0 (not null).
    #   - If current option IS the base case → DB rows just written → final = 0.
    base_case_option_id, base_case_interim = await _get_base_case_emissions(
        db, req.project_stage_instance_id
    )
    base_case_interim_rounded = base_case_interim.quantize(Decimal("0.000001"))
    if base_case_interim_rounded == Decimal("0"):
        # Base case not yet calculated — difference unknown, return 0.
        final_user_emissions = Decimal("0")
    else:
        final_user_emissions = (
            interim_total_rounded - base_case_interim_rounded
        ).quantize(Decimal("0.000001"))

    return AusLargeRoadCalculateResponse(
        project_id=req.project_id,
        project_option_id=req.project_option_id,
        gradient=req.gradient,
        curvature=req.curvature,
        roughness=req.roughness,
        ev_uptake_scenario=req.ev_uptake_scenario,
        anchor_years=req.anchor_years,
        vehicle_results=[
            VehicleTypeAnnualResult(vehicle_type=vt, annual_rows=rows)
            for vt, rows in vehicle_annual_rows.items()
        ],
        interim_total_tco2e=interim_total_rounded,
        base_case_option_id=base_case_option_id,
        base_case_emissions_tco2e=base_case_interim_rounded,
        final_user_emissions_tco2e=final_user_emissions,
    )
