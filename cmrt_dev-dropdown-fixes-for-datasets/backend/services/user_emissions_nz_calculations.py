"""
services/user_emissions_nz_calculations.py

NZ small-project user-emissions (B8) calculation service.

Excel sheet: "NZ example - user emissions (small project)"
Formula for emissions intensity (VEPM linear interpolation):

  intensity = VEPM[year, FLOOR(speed,5)]
            + ((speed - FLOOR(speed,5)) / 5)
            × (VEPM[year, CEIL(speed,5)] - VEPM[year, FLOOR(speed,5)])

  emissions_tco2e = VKT × intensity (gCO2e/km) / 10^6

Interim absolute emissions = SUM(emissions_tco2e) over all years in
  the reference period  [commencement_year … commencement_year + operational_life - 1]

Final user emissions (Option X) = Option X interim − Base case interim
"""

from __future__ import annotations

import uuid as _uuid
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_emissions_nz import UserEmissionsNzResult
from schemas.user_emissions_nz import (
    NzEmissionsAnnualRow,
    NzEmissionsCalculateRequest,
    NzEmissionsCalculateResponse,
)
from services.user_emissions_result_ledger import sync_annual_road_results


# ─────────────────────────────────────────────────────────────────────────────
# VEPM interpolation helper (pure Python — no DB round-trip per vehicle type)
# ─────────────────────────────────────────────────────────────────────────────

def _interpolate(speed: Decimal, low_val: Optional[Decimal], high_val: Optional[Decimal]) -> Optional[Decimal]:
    """
    Linear interpolation between two consecutive 5 km/h VEPM rows.

    If speed is exactly on a 5 km/h boundary, low_val == high_val so the
    (speed - floor) / 5 term is 0 and we just return low_val.
    Returns None if either lookup row was missing.
    """
    if low_val is None or high_val is None:
        return None
    floor_speed = Decimal(int(speed // 5) * 5)
    fraction = (speed - floor_speed) / Decimal(5)
    return low_val + fraction * (high_val - low_val)


# ─────────────────────────────────────────────────────────────────────────────
# VEPM DB lookup — fetches both the floor and ceiling rows in one query
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


async def _lookup_vepm_intensities(
    db: AsyncSession,
    dataset_revision_id: UUID,
    year: int,
    speeds: dict[str, Decimal],   # {"fleet": ..., "light": ..., "heavy": ..., "bus": ...}
) -> dict[str, Optional[Decimal]]:
    """
    Fetches VEPM factors for each vehicle type and applies linear interpolation.
    Returns {"fleet": gCO2e/km, "light": ..., "heavy": ..., "bus": ...}.
    """
    results: dict[str, Optional[Decimal]] = {"fleet": None, "light": None, "heavy": None, "bus": None}

    for vtype, speed in speeds.items():
        if speed is None:
            continue

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

        # Index by speed_kmh
        by_speed: dict[int, dict] = {r["speed_kmh"]: r for r in rows}

        floor_speed = int(speed // 5) * 5
        ceil_speed  = int(-(-speed // 5)) * 5   # ceiling

        col_map = {
            "fleet": "fleet_average_co2e_g_km",
            "light": "light_vehicle_co2e_g_km",
            "heavy": "heavy_vehicle_co2e_g_km",
            "bus": "bus_co2e_g_km",
        }
        col = col_map[vtype]

        low_val  = Decimal(str(by_speed[floor_speed][col])) if floor_speed in by_speed and by_speed[floor_speed][col] is not None else None
        high_val = Decimal(str(by_speed[ceil_speed][col]))  if ceil_speed  in by_speed and by_speed[ceil_speed][col]  is not None else None

        results[vtype] = _interpolate(speed, low_val, high_val)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Project reference-period helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get_project_reference_period(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, int]:
    """
    Returns (commencement_year, operational_life_years) read from the project row.

    commencement_year    = YEAR(project.commencement_of_operations)
    operational_life_years = project.operational_life_years

    Both are mandatory on the project record.  If either is missing a clear
    ValueError is raised so the caller can surface it to the frontend.
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

    commencement_year = row["comm_year"]
    operational_life_years = row["operational_life_years"]

    if commencement_year is None:
        raise ValueError(
            "Project does not have a commencement_of_operations date set. "
            "Please set it before running the user-emissions calculation."
        )
    if operational_life_years is None:
        raise ValueError(
            "Project does not have an operational_life_years value set. "
            "Please set it before running the user-emissions calculation."
        )

    return int(commencement_year), int(operational_life_years)


# ─────────────────────────────────────────────────────────────────────────────
# Fetch base-case option and its interim emissions
# ─────────────────────────────────────────────────────────────────────────────

async def _get_base_case_emissions(
    db: AsyncSession,
    project_stage_instance_id: UUID,
) -> tuple[UUID, Decimal]:
    """
    Finds the base-case option (is_default=true) for a given stage instance
    and returns (base_case_option_id, interim_emissions_tco2e).

    If no base case exists yet, returns the option itself with zero emissions.
    """
    # Find the base case option (is_default=true)
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
            f"No base-case option (is_default=true) found for stage instance {project_stage_instance_id}. "
            "Please designate one option as the base case before calculating user emissions."
        )

    base_case_option_id = base_case_row["id"]

    # Get the interim absolute emissions for the base case option
    interim_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(total_annual_emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_nz_results "
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

async def calculate_and_store_nz(
    db: AsyncSession,
    req: NzEmissionsCalculateRequest,
) -> NzEmissionsCalculateResponse:
    """
    1. Upsert the user-supplied inputs row.
    2. Determine reference period from project (or override).
    3. For each year: look up VEPM intensities + compute per-vehicle-type emissions.
    4. Delete old result rows for this option, insert fresh ones.
    5. Return the full response (annual rows + interim total).

    The caller must commit the session after a successful return.
    """
    # ── 1. Reference period from project dates ────────────────────────────────
    #    Uses project.commencement_of_operations + project.operational_life_years.
    #    NOT hardcoded — the number of years is always read from the project record.
    commencement_year, operational_life_years = await _get_project_reference_period(
        db, req.project_id
    )
    years = list(range(commencement_year, commencement_year + operational_life_years))

    # The project binding is authoritative; only unbound legacy projects fall
    # back to the latest published dataset revision.
    from services.project_context_helper import ProjectContextHelper

    dataset_revision_id: Optional[UUID] = await ProjectContextHelper.fetch_project_dataset_revision(
        db, req.project_id
    )
    if dataset_revision_id is None:
        row = (
            await db.execute(
                text(
                    "SELECT dr.id FROM dataset_revisions dr "
                    "WHERE dr.status = 'published' "
                    "ORDER BY dr.created_at DESC LIMIT 1"
                )
            )
        ).mappings().first()
        if row:
            dataset_revision_id = row["id"]

    if dataset_revision_id is None:
        raise ValueError("No dataset_revision_id available — supply one in the request or publish a dataset revision.")

    # ── 3. Per-year calculation ────────────────────────────────────────────────
    #    Inputs (VKT + speeds) come from the request — NOT from a stored inputs
    #    table.  The frontend passes them directly from activity_data each call.
    annual_rows: list[NzEmissionsAnnualRow] = []

    # ── Determine which vehicle types are present in this request ─────────────
    # Each row (General Fleet / Light Vehicle / Heavy Vehicle / Bus) may be submitted
    # in a separate API call. We upsert only the columns for vehicle types
    # present in this call, preserving whatever was stored from earlier calls.
    has_fleet = req.general_fleet_vkt is not None and req.general_fleet_speed_kmh is not None
    has_light = req.light_vehicle_vkt is not None and req.light_vehicle_speed_kmh is not None
    has_heavy = req.heavy_vehicle_vkt is not None and req.heavy_vehicle_speed_kmh is not None
    has_bus = req.bus_vkt is not None and req.bus_speed_kmh is not None

    speeds_to_lookup: dict[str, Decimal] = {}
    if has_fleet:
        speeds_to_lookup["fleet"] = req.general_fleet_speed_kmh
    if has_light:
        speeds_to_lookup["light"] = req.light_vehicle_speed_kmh
    if has_heavy:
        speeds_to_lookup["heavy"] = req.heavy_vehicle_speed_kmh
    if has_bus:
        speeds_to_lookup["bus"] = req.bus_speed_kmh

    # ── Clamp year to VEPM data range ─────────────────────────────────────────
    # VEPM data only goes up to 2050. For project years beyond 2050, retain
    # the 2050 (flat) intensity values for the remainder of the project life.
    # Confirmed by James Addis, 2026-04-24: "yes please retain flat values for post-2050"
    vepm_range_row = (
        await db.execute(
            text(
                "SELECT MIN(year) AS min_year, MAX(year) AS max_year "
                "FROM vepm_factors WHERE dataset_revision_id = :rid"
            ),
            {"rid": str(dataset_revision_id)},
        )
    ).mappings().first()
    vepm_min_year: Optional[int] = int(vepm_range_row["min_year"]) if vepm_range_row and vepm_range_row["min_year"] is not None else None
    vepm_max_year: Optional[int] = int(vepm_range_row["max_year"]) if vepm_range_row and vepm_range_row["max_year"] is not None else None

    # ── Per-year upsert ───────────────────────────────────────────────────────
    # INSERT new row, or on conflict update ONLY the submitted vehicle type
    # columns (COALESCE keeps existing values for other vehicle types).
    # total_annual_emissions_tco2e is recomputed from the merged values.
    t = UserEmissionsNzResult.__table__

    def _emissions(vkt: Optional[Decimal], intensity: Optional[Decimal]) -> Optional[Decimal]:
        """Returns tCO2e, or None if either input is absent."""
        if vkt is None or intensity is None:
            return None
        return (vkt * intensity / Decimal("1000000")).quantize(Decimal("0.000001"))

    for year in years:
        # Clamp to the VEPM data range so years beyond 2050 (or before min)
        # reuse the nearest available intensity rather than returning None.
        lookup_year = year
        if vepm_max_year is not None and lookup_year > vepm_max_year:
            lookup_year = vepm_max_year
        if vepm_min_year is not None and lookup_year < vepm_min_year:
            lookup_year = vepm_min_year

        intensities = await _lookup_vepm_intensities(
            db,
            dataset_revision_id=dataset_revision_id,
            year=lookup_year,
            speeds=speeds_to_lookup,
        )

        fleet_int = intensities.get("fleet") if has_fleet else None
        light_int = intensities.get("light") if has_light else None
        heavy_int = intensities.get("heavy") if has_heavy else None
        bus_int = intensities.get("bus") if has_bus else None

        fleet_em = _emissions(req.general_fleet_vkt, fleet_int) if has_fleet else None
        light_em = _emissions(req.light_vehicle_vkt, light_int) if has_light else None
        heavy_em = _emissions(req.heavy_vehicle_vkt, heavy_int) if has_heavy else None
        bus_em = _emissions(req.bus_vkt, bus_int) if has_bus else None

        # total for INSERT case (no prior row): sum of what's provided
        this_total = (
            (fleet_em or Decimal("0"))
            + (light_em or Decimal("0"))
            + (heavy_em or Decimal("0"))
            + (bus_em or Decimal("0"))
        )

        ins = pg_insert(UserEmissionsNzResult).values(
            id=_uuid.uuid4(),
            project_id=req.project_id,
            project_stage_instance_id=req.project_stage_instance_id,
            project_option_id=req.project_option_id,
            assessment_year=year,
            general_fleet_intensity_gco2e_km=fleet_int,
            light_vehicle_intensity_gco2e_km=light_int,
            heavy_vehicle_intensity_gco2e_km=heavy_int,
            bus_intensity_gco2e_km=bus_int,
            general_fleet_emissions_tco2e=fleet_em,
            light_vehicle_emissions_tco2e=light_em,
            heavy_vehicle_emissions_tco2e=heavy_em,
            bus_emissions_tco2e=bus_em,
            total_annual_emissions_tco2e=this_total,
        )
        await db.execute(
            ins.on_conflict_do_update(
                constraint="uq_user_emissions_nz_results",
                set_={
                    # Keep new value if provided; else preserve existing column
                    "general_fleet_intensity_gco2e_km": func.coalesce(
                        ins.excluded.general_fleet_intensity_gco2e_km,
                        t.c.general_fleet_intensity_gco2e_km,
                    ),
                    "light_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.light_vehicle_intensity_gco2e_km,
                        t.c.light_vehicle_intensity_gco2e_km,
                    ),
                    "heavy_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.heavy_vehicle_intensity_gco2e_km,
                        t.c.heavy_vehicle_intensity_gco2e_km,
                    ),
                    "bus_intensity_gco2e_km": func.coalesce(
                        ins.excluded.bus_intensity_gco2e_km,
                        t.c.bus_intensity_gco2e_km,
                    ),
                    "general_fleet_emissions_tco2e": func.coalesce(
                        ins.excluded.general_fleet_emissions_tco2e,
                        t.c.general_fleet_emissions_tco2e,
                    ),
                    "light_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.light_vehicle_emissions_tco2e,
                        t.c.light_vehicle_emissions_tco2e,
                    ),
                    "heavy_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.heavy_vehicle_emissions_tco2e,
                        t.c.heavy_vehicle_emissions_tco2e,
                    ),
                    "bus_emissions_tco2e": func.coalesce(
                        ins.excluded.bus_emissions_tco2e,
                        t.c.bus_emissions_tco2e,
                    ),
                    # Recompute total from merged (new OR existing) values
                    "total_annual_emissions_tco2e": (
                        func.coalesce(
                            ins.excluded.general_fleet_emissions_tco2e,
                            t.c.general_fleet_emissions_tco2e,
                            Decimal("0"),
                        )
                        + func.coalesce(
                            ins.excluded.light_vehicle_emissions_tco2e,
                            t.c.light_vehicle_emissions_tco2e,
                            Decimal("0"),
                        )
                        + func.coalesce(
                            ins.excluded.heavy_vehicle_emissions_tco2e,
                            t.c.heavy_vehicle_emissions_tco2e,
                            Decimal("0"),
                        )
                        + func.coalesce(
                            ins.excluded.bus_emissions_tco2e,
                            t.c.bus_emissions_tco2e,
                            Decimal("0"),
                        )
                    ),
                },
            )
        )

    # ── Interim total: re-read from DB so it includes ALL vehicle types ───────
    # (earlier calls may have stored general fleet; this call adds light etc.)
    total_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(total_annual_emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_nz_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(req.project_option_id)},
        )
    ).mappings().first()
    interim_total = Decimal(str(total_row["interim_total"])).quantize(Decimal("0.0001"))

    # ── 4. Fetch base case and calculate final user emissions ────────────────
    # Rules (confirmed with James Addis):
    #   - Base case option is the one with is_default=true in project_options.
    #   - If the base case has no results yet (not yet calculated), treat its
    #     emissions as equal to this option's interim → final = 0.
    #   - If the current option IS the base case, its DB rows are already written
    #     above, so base_case_interim == interim_total → final = 0.
    base_case_option_id, base_case_interim = await _get_base_case_emissions(
        db, req.project_stage_instance_id
    )
    base_case_interim_rounded = base_case_interim.quantize(Decimal("0.0001"))
    if base_case_interim_rounded == Decimal("0"):
        # Base case not yet calculated — difference is unknown, show 0.
        # base_case_emissions_tco2e stays 0 in the response.
        final_user_emissions = Decimal("0")
    else:
        final_user_emissions = (interim_total - base_case_interim_rounded).quantize(Decimal("0.0001"))

    await sync_annual_road_results(db, project_option_id=req.project_option_id, project_class="SMALL", is_nz=True)
    return NzEmissionsCalculateResponse(
        project_id=req.project_id,
        project_stage_instance_id=req.project_stage_instance_id,
        project_option_id=req.project_option_id,
        commencement_year=commencement_year,
        operational_life_years=operational_life_years,
        interim_absolute_emissions_tco2e=interim_total,
        base_case_option_id=base_case_option_id,
        base_case_emissions_tco2e=base_case_interim_rounded,
        final_user_emissions_tco2e=final_user_emissions,
        # annual_rows=annual_rows,  # uncomment to include per-year breakdown
    )
