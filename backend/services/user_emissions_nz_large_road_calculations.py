"""
services/user_emissions_nz_large_road_calculations.py

NZ large-project road user-emissions (B8) calculation service.

Large-project difference vs. small (user_emissions_nz_calculations.py):
  - User supplies VKT + speed for SPECIFIC modelled years (anchor points).
  - All other reference-period years are filled by interpolation or
    extrapolation using those anchor points.
  - One API call per vehicle type; missing vehicle types produce no rows.
  - VKT and speed are stored per year (for audit) in a dedicated table
    user_emissions_nz_large_road_results.

No road parameters (gradient / curvature / roughness) are used —
NZ calculations use VEPM factors which depend only on year and speed.

Interpolation / extrapolation rules (identical to AUS Large):
  Y < first anchor year  : flat at first anchor values (carry-back)
  first ≤ Y ≤ last       : piecewise linear interpolation
  Y > last anchor year   : linear extrapolation from the last two anchors
                           (FORECAST.LINEAR equivalent)
  Single anchor          : flat value for all years

VEPM column mapping (vehicle_type → vepm_factors column):
  general_fleet  → fleet_average_co2e_g_km
  light_vehicle  → light_vehicle_co2e_g_km
  heavy_vehicle  → heavy_vehicle_co2e_g_km
  bus            → bus_co2e_g_km

Emission formula:
  emissions_tco2e = VKT_calc × intensity_gco2e_km / 1,000,000
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func as sa_func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_emissions_nz_large_road import UserEmissionsNzLargeRoadResult
from schemas.user_emissions_nz_large_road import (
    NzLargeRoadAnnualRow,
    NzLargeRoadCalculateRequest,
    NzLargeRoadCalculateResponse,
    NzVehicleTypeAnnualResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# VEPM column mapping
# ─────────────────────────────────────────────────────────────────────────────

_VEPM_COL_MAP: dict[str, str] = {
    "general_fleet": "fleet_average_co2e_g_km",
    "light_vehicle": "light_vehicle_co2e_g_km",
    "heavy_vehicle": "heavy_vehicle_co2e_g_km",
    "bus":           "bus_co2e_g_km",
}

# ─────────────────────────────────────────────────────────────────────────────
# VEPM interpolation helper
# ─────────────────────────────────────────────────────────────────────────────

def _interpolate(
    speed: Decimal,
    low_val: Optional[Decimal],
    high_val: Optional[Decimal],
) -> Optional[Decimal]:
    """
    Linear interpolation between consecutive 5 km/h VEPM rows.

    If speed is exactly on a 5 km/h boundary, low_val == high_val and the
    fraction term is 0, so low_val is returned unchanged.
    Returns None when either lookup row is missing.
    """
    if low_val is None or high_val is None:
        return None
    floor_speed = Decimal(int(speed // 5) * 5)
    fraction = (speed - floor_speed) / Decimal(5)
    return low_val + fraction * (high_val - low_val)


# ─────────────────────────────────────────────────────────────────────────────
# VEPM DB lookup for a single vehicle type
# ─────────────────────────────────────────────────────────────────────────────

_VEPM_SQL = text("""
    SELECT
        speed_kmh,
        fleet_average_co2e_g_km,
        light_vehicle_co2e_g_km,
        heavy_vehicle_co2e_g_km,
        bus_co2e_g_km
    FROM vepm_factors
    WHERE dataset_revision_id = :dataset_revision_id
      AND year = :year
      AND speed_kmh IN (
            (FLOOR(:speed_kmh / 5.0) * 5)::int,
            (CEIL(:speed_kmh  / 5.0) * 5)::int
          )
    ORDER BY speed_kmh
""")


async def _lookup_vepm_intensity(
    db: AsyncSession,
    dataset_revision_id: UUID,
    year: int,
    speed: Decimal,
    vehicle_type: str,
) -> Optional[Decimal]:
    """
    Looks up the interpolated VEPM intensity (gCO2e/km) for a single vehicle
    type at a given year and speed.  Returns None if the data is absent.
    """
    col = _VEPM_COL_MAP.get(vehicle_type)
    if col is None:
        return None

    rows = (
        await db.execute(
            _VEPM_SQL,
            {
                "dataset_revision_id": str(dataset_revision_id),
                "year": year,
                "speed_kmh": float(speed),
            },
        )
    ).mappings().all()

    by_speed: dict[int, dict] = {r["speed_kmh"]: r for r in rows}

    floor_speed = int(speed // 5) * 5
    ceil_speed  = floor_speed if speed % 5 == 0 else floor_speed + 5  # exact or next band

    low_val  = (
        Decimal(str(by_speed[floor_speed][col]))
        if floor_speed in by_speed and by_speed[floor_speed][col] is not None
        else None
    )
    high_val = (
        Decimal(str(by_speed[ceil_speed][col]))
        if ceil_speed in by_speed and by_speed[ceil_speed][col] is not None
        else None
    )

    return _interpolate(speed, low_val, high_val)


# ─────────────────────────────────────────────────────────────────────────────
# Project reference-period helper  (NZ — no state_name needed)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_project_reference_period(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, int]:
    """
    Returns (commencement_year, operational_life_years).
    Both are read from the project record and must be set.
    """
    row = (
        await db.execute(
            text(
                "SELECT EXTRACT(YEAR FROM commencement_of_operations)::int AS comm_year,"
                "       operational_life_years"
                "  FROM project WHERE id = :pid"
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

    return int(row["comm_year"]), int(row["operational_life_years"])


# ─────────────────────────────────────────────────────────────────────────────
# VEPM dataset revision + year-range helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_vepm_dataset_revision_id(db: AsyncSession) -> UUID:
    """Returns the latest published dataset_revision_id."""
    row = (
        await db.execute(
            text(
                "SELECT id FROM dataset_revisions "
                "WHERE status = 'published' "
                "ORDER BY created_at DESC LIMIT 1"
            )
        )
    ).mappings().first()
    if row is None:
        raise ValueError(
            "No published dataset revision found. "
            "Publish a dataset revision before running NZ calculations."
        )
    return row["id"]


async def _get_vepm_year_range(
    db: AsyncSession,
    dataset_revision_id: UUID,
) -> tuple[int, int]:
    """Returns (min_year, max_year) for the given VEPM dataset revision."""
    row = (
        await db.execute(
            text(
                "SELECT MIN(year) AS min_year, MAX(year) AS max_year "
                "FROM vepm_factors WHERE dataset_revision_id = :rid"
            ),
            {"rid": str(dataset_revision_id)},
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
    year:      int
    vkt:       Decimal
    speed_kmh: Decimal


# ─────────────────────────────────────────────────────────────────────────────
# Interpolation / extrapolation (matches Excel formulas)
# ─────────────────────────────────────────────────────────────────────────────

def _build_year_values(
    anchors: list[_SimpleAnchor],
    ref_years: list[int],
) -> dict[int, tuple[Decimal, Decimal]]:
    """
    Returns {assessment_year: (vkt, speed_kmh)} for every year in ref_years.

    Rules:
      Y < first anchor year : flat at first anchor (carry-back)
      first ≤ Y ≤ last      : piecewise linear interpolation
      Y > last anchor year  : linear extrapolation from the last two anchors
                              (FORECAST.LINEAR equivalent)
      Single anchor         : flat value for all years
    """
    sorted_anchors = sorted(anchors, key=lambda a: a.year)
    result: dict[int, tuple[Decimal, Decimal]] = {}

    for Y in ref_years:
        if len(sorted_anchors) == 1 or Y <= sorted_anchors[0].year:
            # Single anchor or before first anchor — flat carry-back
            result[Y] = (sorted_anchors[0].vkt, sorted_anchors[0].speed_kmh)

        elif Y >= sorted_anchors[-1].year:
            if len(sorted_anchors) >= 2:
                # Extrapolate from last two anchors
                a = sorted_anchors[-2]
                b = sorted_anchors[-1]
                dy    = Decimal(str(b.year - a.year))
                t     = Decimal(str(Y - a.year)) / dy
                vkt   = a.vkt       + (b.vkt       - a.vkt)       * t
                speed = a.speed_kmh + (b.speed_kmh - a.speed_kmh) * t
                result[Y] = (vkt, speed)
            else:
                result[Y] = (sorted_anchors[-1].vkt, sorted_anchors[-1].speed_kmh)

        else:
            # Piecewise linear between consecutive anchors
            for i in range(len(sorted_anchors) - 1):
                a = sorted_anchors[i]
                b = sorted_anchors[i + 1]
                if a.year <= Y <= b.year:
                    dy    = Decimal(str(b.year - a.year))
                    t     = Decimal(str(Y - a.year)) / dy
                    vkt   = a.vkt       + (b.vkt       - a.vkt)       * t
                    speed = a.speed_kmh + (b.speed_kmh - a.speed_kmh) * t
                    result[Y] = (vkt, speed)
                    break

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Base-case option helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get_base_case_emissions(
    db: AsyncSession,
    project_stage_instance_id: UUID,
) -> tuple[UUID, Decimal]:
    """
    Finds the base-case option (is_default=true) for the stage instance and returns
    (base_case_option_id, interim_emissions_tco2e).

    interim_emissions_tco2e is the SUM across ALL vehicle types stored in
    user_emissions_nz_large_road_results for that option.
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
                "FROM user_emissions_nz_large_road_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(base_case_option_id)},
        )
    ).mappings().first()

    interim_emissions = Decimal(interim_row["interim_total"]) if interim_row else Decimal("0")
    return base_case_option_id, interim_emissions


# ─────────────────────────────────────────────────────────────────────────────
# Main calculation entry point
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_and_store_nz_large_road(
    db: AsyncSession,
    req: NzLargeRoadCalculateRequest,
) -> NzLargeRoadCalculateResponse:
    """
    Calculates and stores NZ large-project road user emissions for all vehicle types
    submitted in this call (one or more).

    Steps:
      1. Resolve reference period (commencement year + operational life).
      2. Group anchor data by vehicle_type across all anchor years.
      3. Interpolate/extrapolate (VKT, speed) for every reference-period year per type.
      4. Resolve VEPM dataset revision + clamp year range.
      5. For each vehicle type × year: look up VEPM intensity, compute emissions, upsert.
      6. Re-read option total from DB (all vehicle types stored so far).
      7. Fetch base case from DB, compute final user emissions.
      8. Return response with vehicle_results (not serialised) + option-level totals.

    The caller must commit the session after a successful return.
    """

    # ── 1. Reference period ───────────────────────────────────────────────────
    commencement_year, operational_life_years = await _get_project_reference_period(
        db, req.project_id
    )
    ref_years = list(range(commencement_year, commencement_year + operational_life_years))

    # ── 2. Group anchor data by vehicle_type ──────────────────────────────────
    vehicle_anchors: dict[str, list[_SimpleAnchor]] = {}
    for ay in req.anchor_years:
        for v in ay.vehicles:
            vehicle_anchors.setdefault(v.vehicle_type, []).append(
                _SimpleAnchor(year=ay.year, vkt=v.vkt, speed_kmh=v.speed_kmh)
            )

    # ── 3. Interpolate/extrapolate per vehicle type ───────────────────────────
    vehicle_year_values: dict[str, dict[int, tuple[Decimal, Decimal]]] = {
        vt: _build_year_values(anchors, ref_years)
        for vt, anchors in vehicle_anchors.items()
    }

    # ── 4. Dataset revision + VEPM year range ─────────────────────────────────
    dataset_revision_id = await _get_vepm_dataset_revision_id(db)
    vepm_min_year, vepm_max_year = await _get_vepm_year_range(db, dataset_revision_id)

    # ── 5. Per-year, per-vehicle-type calculation + upsert ────────────────────
    vehicle_annual_rows: dict[str, list[NzLargeRoadAnnualRow]] = {
        vt: [] for vt in vehicle_anchors
    }

    for year in ref_years:
        lookup_year = max(vepm_min_year, min(year, vepm_max_year))

        for vt, year_vals in vehicle_year_values.items():
            vkt_calc, speed_calc = year_vals[year]

            vkt_q   = vkt_calc.quantize(Decimal("0.000001"))
            speed_q = speed_calc.quantize(Decimal("0.0001"))

            intensity = await _lookup_vepm_intensity(
                db,
                dataset_revision_id=dataset_revision_id,
                year=lookup_year,
                speed=speed_q,
                vehicle_type=vt,
            )

            emissions = (
                (vkt_q * intensity / Decimal("1000000")).quantize(Decimal("0.000001"))
                if intensity is not None
                else None
            )

            vehicle_annual_rows[vt].append(
                NzLargeRoadAnnualRow(
                    assessment_year=year,
                    vkt_calc=vkt_q,
                    speed_kph_calc=speed_q,
                    emissions_intensity_gco2e_km=intensity,
                    emissions_tco2e=emissions,
                )
            )

            ins = pg_insert(UserEmissionsNzLargeRoadResult).values(
                id=_uuid.uuid4(),
                project_id=req.project_id,
                project_stage_instance_id=req.project_stage_instance_id,
                project_option_id=req.project_option_id,
                vehicle_type=vt,
                assessment_year=year,
                vkt_calc=vkt_q,
                speed_kph_calc=speed_q,
                emissions_intensity_gco2e_km=intensity,
                emissions_tco2e=emissions,
            )
            await db.execute(
                ins.on_conflict_do_update(
                    constraint="uq_nz_large_road_option_vehicle_year",
                    set_={
                        "vkt_calc":                     ins.excluded.vkt_calc,
                        "speed_kph_calc":               ins.excluded.speed_kph_calc,
                        "emissions_intensity_gco2e_km": ins.excluded.emissions_intensity_gco2e_km,
                        "emissions_tco2e":              ins.excluded.emissions_tco2e,
                        "created_at":                   sa_func.now(),
                    },
                )
            )

    # ── 6. Interim total: re-read from DB (all vehicle types for this option) ──
    total_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_nz_large_road_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(req.project_option_id)},
        )
    ).mappings().first()
    interim_total = Decimal(str(total_row["interim_total"])).quantize(Decimal("0.000001"))

    # ── 7. Base case + final user emissions ───────────────────────────────────
    base_case_option_id, base_case_interim = await _get_base_case_emissions(
        db, req.project_stage_instance_id
    )
    base_case_interim_rounded = base_case_interim.quantize(Decimal("0.000001"))

    if base_case_interim_rounded == Decimal("0"):
        final_user_emissions = Decimal("0")
    else:
        final_user_emissions = (
            interim_total - base_case_interim_rounded
        ).quantize(Decimal("0.000001"))

    return NzLargeRoadCalculateResponse(
        project_id=req.project_id,
        project_option_id=req.project_option_id,
        anchor_years=req.anchor_years,
        vehicle_results=[
            NzVehicleTypeAnnualResult(vehicle_type=vt, annual_rows=rows)
            for vt, rows in vehicle_annual_rows.items()
        ],
        interim_total_tco2e=interim_total,
        base_case_option_id=base_case_option_id,
        base_case_emissions_tco2e=base_case_interim_rounded,
        final_user_emissions_tco2e=final_user_emissions,
    )
