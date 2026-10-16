"""
services/user_emissions_aus_small_calculations.py

AUS small-project user-emissions (B8) calculation service.

Excel sheet: "Australian Example - Small projects"

The four frontend vehicle types map to ATAP vehicle classes:
  Light vehicle       → Medium Car           (frontend label: "Light vehicle")
  Medium vehicle      → Courier Van-Utility  (frontend label: "Medium vehicle")
  Heavy vehicle       → Heavy Rigid          (frontend label: "Heavy vehicle")
  Super heavy vehicle → B-Double             (frontend label: "Super heavy vehicle")

Emissions intensity is derived by calling fn_veh_emissions_intensity_aus for
each year in the reference period, using:
  - p_year       — the assessment year
  - p_state      — resolved from project → organization.region_id → jurisdictions.name
  - p_scenario   — always "Step Change" (fixed for small projects)
  - p_gradient   — 0     (flat — default for small projects)
  - p_curvature  — 20    (default curvature for small projects)
  - p_iri        — 2.0   (default IRI for small projects)
  - p_speed_kph  — from the request (per vehicle type)

VKT and speed are constant across all years (user enters 1 year of data).

Formula:
  emissions_tco2e = VKT × fleet_avg_emissions_intensity_gco2e_per_vkt / 10^6

Interim absolute emissions = SUM(total_annual_emissions_tco2e) across all years.
Final user emissions = interim − base_case_emissions_tco2e.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from collections import defaultdict
from decimal import Decimal
from time import perf_counter
from typing import Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_emissions_aus_small import UserEmissionsAusSmallResult
from schemas.user_emissions_aus_small import (
    AusSmallEmissionsCalculateRequest,
    AusSmallEmissionsCalculateResponse,
)
from services.user_emissions_result_ledger import sync_annual_road_results
from services.aus_road_emissions_batch import (
    AUS_INTENSITY_BATCH_SQL,
    build_aus_intensity_pairs,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Vehicle class mapping: request field prefix → ATAP vehicle class name
# ─────────────────────────────────────────────────────────────────────────────

VEHICLE_CLASS_MAP: dict[str, str] = {
    "light_vehicle":       "Medium Car",
    "medium_vehicle":      "Courier Van-Utility",
    "heavy_vehicle":       "Heavy Rigid",
    "super_heavy_vehicle": "B-Double",
}

# EV uptake scenario — always Step Change for small projects
_SCENARIO: str = "Step Change"

# Default road parameters for small projects
# "moderate / straight / smooth" as confirmed by James:
#   moderate  → gradient  = 40 m/km  (0=flat, 40=rolling, 60=moderate, 80=hilly)
#   straight  → curvature = 20 deg/km (lowest discrete value in lookup)
#   smooth    → IRI       = 2.0 m/km  (continuous input, standard smooth road)
_DEFAULT_GRADIENT:  float = 40.0
_DEFAULT_CURVATURE: float = 20.0
_DEFAULT_IRI:       float = 2.0

# ─────────────────────────────────────────────────────────────────────────────
# SQL — calls fn_veh_emissions_intensity_aus for a given year + speed
# Returns all vehicle classes; we filter in Python for the 4 we need.
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Project reference-period helper (same pattern as NZ service)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_project_reference_period(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, int, str]:
    """
    Returns (commencement_year, operational_life_years, state_name) from the
    project row, joined through organization → jurisdiction (region).
    Raises ValueError if the project is not found, dates are missing, or no
    region is set on the proponent org.
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

    commencement_year      = row["comm_year"]
    operational_life_years = row["operational_life_years"]
    state_name             = row["state_name"]

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
    if state_name is None:
        raise ValueError(
            "The proponent organisation for this project does not have a region set. "
            "Please update the organisation's region before running the AUS calculation."
        )

    return int(commencement_year), int(operational_life_years), state_name


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
                "FROM user_emissions_aus_small_results "
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

async def calculate_and_store_aus_small(
    db: AsyncSession,
    req: AusSmallEmissionsCalculateRequest,
) -> AusSmallEmissionsCalculateResponse:
    """
    1. Resolve reference period from the project row.
    2. Group the 4 vehicle types by speed and fetch all year/speed intensities
       with one database round trip.
    3. Compute annual emissions and upsert annual result rows in one batch.
    4. Synchronize the calculated annual totals into the shared result ledger.
    5. Compute interim total and final user emissions.
    6. Return full response.

    The caller must commit the session after a successful return.
    """
    calculation_started_at = perf_counter()
    # ── 1. Reference period ───────────────────────────────────────────────────
    commencement_year, operational_life_years, state_name = await _get_project_reference_period(
        db, req.project_id
    )
    from services.project_context_helper import ProjectContextHelper

    dataset_revision_id = await ProjectContextHelper.fetch_project_dataset_revision(db, req.project_id)
    if dataset_revision_id is None:
        raise ValueError("No dataset revision is selected for this project.")
    years = list(range(commencement_year, commencement_year + operational_life_years))

    # ── 2. Group vehicle types by speed ───────────────────────────────────────
    # speed_to_v_keys: { speed_value → [vehicle_key, ...] }
    # Vehicle types with None speed are skipped (their emissions will be None).
    speed_to_v_keys: dict[float, list[str]] = defaultdict(list)
    for v_key in VEHICLE_CLASS_MAP:
        speed = getattr(req, f"{v_key}_speed_kmh")
        if speed is not None:
            speed_to_v_keys[float(speed)].append(v_key)

    # ── 3. Determine which vehicle types are present in this request ──────────
    # Each vehicle type may be submitted in a separate API call. We upsert only
    # the columns present in this call, preserving earlier calls' data.
    has_light       = req.light_vehicle_vkt       is not None
    has_medium      = req.medium_vehicle_vkt      is not None
    has_heavy       = req.heavy_vehicle_vkt       is not None
    has_super_heavy = req.super_heavy_vehicle_vkt is not None

    t = UserEmissionsAusSmallResult.__table__

    # ── 4. Clamp year to available data range ────────────────────────────────
    # ev_uptake_factors and electric_decarb_factors only go up to a certain year
    # (currently 2050). For project years beyond that, retain the last year's
    # flat intensity values for the remainder of the project life.
    # Confirmed by James Addis, 2026-04-24: "yes please retain flat values for post-2050"
    aus_range_row = (
        await db.execute(
            text(
                "SELECT LEAST("
                "    (SELECT MAX(year) FROM ev_uptake_factors WHERE dataset_revision_id = :dataset_revision_id),"
                "    (SELECT MAX(year) FROM electric_decarb_factors WHERE dataset_revision_id = :dataset_revision_id)"
                ") AS max_year,"
                "GREATEST("
                "    (SELECT MIN(year) FROM ev_uptake_factors WHERE dataset_revision_id = :dataset_revision_id),"
                "    (SELECT MIN(year) FROM electric_decarb_factors WHERE dataset_revision_id = :dataset_revision_id)"
                ") AS min_year"
            ),
            {"dataset_revision_id": str(dataset_revision_id)},
        )
    ).mappings().first()
    aus_min_year: Optional[int] = int(aus_range_row["min_year"]) if aus_range_row and aus_range_row["min_year"] is not None else None
    aus_max_year: Optional[int] = int(aus_range_row["max_year"]) if aus_range_row and aus_range_row["max_year"] is not None else None

    # ── 5. Fetch all required intensities in one database round trip ──────────
    requested_pairs = build_aus_intensity_pairs(
        years, sorted(speed_to_v_keys), aus_min_year, aus_max_year
    )
    intensity_started_at = perf_counter()
    intensity_rows = []
    if requested_pairs:
        intensity_rows = (
            await db.execute(
                AUS_INTENSITY_BATCH_SQL,
                {
                    "requested_pairs": json.dumps(requested_pairs),
                    "p_state": state_name,
                    "p_scenario": _SCENARIO,
                    "p_gradient": _DEFAULT_GRADIENT,
                    "p_curvature": _DEFAULT_CURVATURE,
                    "p_iri": _DEFAULT_IRI,
                    "p_dataset_revision_id": str(dataset_revision_id),
                },
            )
        ).mappings().all()
    intensity_lookup: dict[tuple[int, float], dict[str, Decimal]] = defaultdict(dict)
    for row in intensity_rows:
        value = row["fleet_avg_emissions_intensity_gco2e_per_vkt"]
        if value is not None:
            intensity_lookup[(int(row["assessment_year"]), float(row["speed_kph"]))][
                row["vehicle_class"]
            ] = Decimal(str(value))
    intensity_elapsed_ms = (perf_counter() - intensity_started_at) * 1000

    # ── 6. Compute annual emissions and collect result writes ─────────────────
    annual_upserts: list[dict[str, object]] = []

    for year in years:
        # Clamp lookup year to available data range
        lookup_year = year
        if aus_max_year is not None and lookup_year > aus_max_year:
            lookup_year = aus_max_year
        if aus_min_year is not None and lookup_year < aus_min_year:
            lookup_year = aus_min_year

        intensities: dict[str, Optional[Decimal]] = {k: None for k in VEHICLE_CLASS_MAP}
        for v_key in VEHICLE_CLASS_MAP:
            speed = getattr(req, f"{v_key}_speed_kmh")
            if speed is None:
                continue
            class_to_intensity = intensity_lookup.get((lookup_year, float(speed)), {})
            intensities[v_key] = class_to_intensity.get(VEHICLE_CLASS_MAP[v_key])

        # Compute per-vehicle annual emissions (tCO2e = VKT × gCO2e/km / 1e6)
        def _emissions(v_key: str) -> Optional[Decimal]:
            vkt       = getattr(req, f"{v_key}_vkt")
            intensity = intensities[v_key]
            if vkt is None or intensity is None:
                return None
            return (Decimal(str(vkt)) * intensity / Decimal("1000000")).quantize(
                Decimal("0.0000000001")
            )

        light_em       = _emissions("light_vehicle")
        medium_em      = _emissions("medium_vehicle")
        heavy_em       = _emissions("heavy_vehicle")
        super_heavy_em = _emissions("super_heavy_vehicle")

        # For INSERT case (no prior row): total = sum of what's provided now
        this_total = (
            (light_em       or Decimal("0"))
            + (medium_em    or Decimal("0"))
            + (heavy_em     or Decimal("0"))
            + (super_heavy_em or Decimal("0"))
        )

        annual_upserts.append({
            "id": _uuid.uuid4(),
            "project_id": req.project_id,
            "project_stage_instance_id": req.project_stage_instance_id,
            "project_option_id": req.project_option_id,
            "assessment_year": year,
            "light_vehicle_intensity_gco2e_km": intensities["light_vehicle"] if has_light else None,
            "medium_vehicle_intensity_gco2e_km": intensities["medium_vehicle"] if has_medium else None,
            "heavy_vehicle_intensity_gco2e_km": intensities["heavy_vehicle"] if has_heavy else None,
            "super_heavy_vehicle_intensity_gco2e_km": intensities["super_heavy_vehicle"] if has_super_heavy else None,
            "light_vehicle_emissions_tco2e": light_em if has_light else None,
            "medium_vehicle_emissions_tco2e": medium_em if has_medium else None,
            "heavy_vehicle_emissions_tco2e": heavy_em if has_heavy else None,
            "super_heavy_vehicle_emissions_tco2e": super_heavy_em if has_super_heavy else None,
            "total_annual_emissions_tco2e": this_total,
        })

    annual_write_started_at = perf_counter()
    if annual_upserts:
        ins = pg_insert(UserEmissionsAusSmallResult).values(annual_upserts)
        await db.execute(
            ins.on_conflict_do_update(
                constraint="uq_user_emissions_aus_small_results",
                set_={
                    # Keep new value if provided; else preserve existing
                    "light_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.light_vehicle_intensity_gco2e_km,
                        t.c.light_vehicle_intensity_gco2e_km,
                    ),
                    "medium_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.medium_vehicle_intensity_gco2e_km,
                        t.c.medium_vehicle_intensity_gco2e_km,
                    ),
                    "heavy_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.heavy_vehicle_intensity_gco2e_km,
                        t.c.heavy_vehicle_intensity_gco2e_km,
                    ),
                    "super_heavy_vehicle_intensity_gco2e_km": func.coalesce(
                        ins.excluded.super_heavy_vehicle_intensity_gco2e_km,
                        t.c.super_heavy_vehicle_intensity_gco2e_km,
                    ),
                    "light_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.light_vehicle_emissions_tco2e,
                        t.c.light_vehicle_emissions_tco2e,
                    ),
                    "medium_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.medium_vehicle_emissions_tco2e,
                        t.c.medium_vehicle_emissions_tco2e,
                    ),
                    "heavy_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.heavy_vehicle_emissions_tco2e,
                        t.c.heavy_vehicle_emissions_tco2e,
                    ),
                    "super_heavy_vehicle_emissions_tco2e": func.coalesce(
                        ins.excluded.super_heavy_vehicle_emissions_tco2e,
                        t.c.super_heavy_vehicle_emissions_tco2e,
                    ),
                    # Recompute total from merged (new OR existing) values
                    "total_annual_emissions_tco2e": (
                        func.coalesce(ins.excluded.light_vehicle_emissions_tco2e,       t.c.light_vehicle_emissions_tco2e,       Decimal("0"))
                        + func.coalesce(ins.excluded.medium_vehicle_emissions_tco2e,    t.c.medium_vehicle_emissions_tco2e,    Decimal("0"))
                        + func.coalesce(ins.excluded.heavy_vehicle_emissions_tco2e,     t.c.heavy_vehicle_emissions_tco2e,     Decimal("0"))
                        + func.coalesce(ins.excluded.super_heavy_vehicle_emissions_tco2e, t.c.super_heavy_vehicle_emissions_tco2e, Decimal("0"))
                    ),
                },
            )
        )

    annual_write_elapsed_ms = (perf_counter() - annual_write_started_at) * 1000

    # ── Interim total: re-read from DB so it includes ALL vehicle types ─────────
    # (earlier calls may have stored light only; this call may add heavy etc.)
    summary_started_at = perf_counter()
    total_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(total_annual_emissions_tco2e), 0) AS interim_total "
                "FROM user_emissions_aus_small_results "
                "WHERE project_option_id = :opt_id"
            ),
            {"opt_id": str(req.project_option_id)},
        )
    ).mappings().first()
    interim_total_rounded = Decimal(str(total_row["interim_total"])).quantize(Decimal("0.0001"))

    # ── 5. Fetch base case and calculate final user emissions ─────────────────
    # Rules (confirmed with James Addis):
    #   - Base case option is the one with is_default=true in project_options.
    #   - If the base case has no results yet (not yet calculated), show final = 0.
    #   - If the current option IS the base case, difference = 0 naturally.
    base_case_option_id, base_case_interim = await _get_base_case_emissions(
        db, req.project_stage_instance_id
    )
    base_case_interim_rounded = base_case_interim.quantize(Decimal("0.0001"))
    if base_case_interim_rounded == Decimal("0"):
        # Base case not yet calculated — difference is unknown, show 0.
        # base_case_emissions_tco2e stays 0 in the response.
        final_user_emissions = Decimal("0")
    else:
        final_user_emissions = (interim_total_rounded - base_case_interim_rounded).quantize(Decimal("0.0001"))

    summary_elapsed_ms = (perf_counter() - summary_started_at) * 1000
    ledger_started_at = perf_counter()
    await sync_annual_road_results(db, project_option_id=req.project_option_id, project_class="SMALL", is_nz=False)
    ledger_elapsed_ms = (perf_counter() - ledger_started_at) * 1000
    logger.info(
        "AUS small road calculation timing: years=%d distinct_speeds=%d intensity_pairs=%d "
        "intensity_batch_ms=%.1f annual_upsert_rows=%d annual_upsert_ms=%.1f "
        "summary_queries_ms=%.1f ledger_sync_ms=%.1f total_ms=%.1f",
        len(years), len(speed_to_v_keys), len(requested_pairs), intensity_elapsed_ms,
        len(annual_upserts), annual_write_elapsed_ms, summary_elapsed_ms,
        ledger_elapsed_ms, (perf_counter() - calculation_started_at) * 1000,
    )
    return AusSmallEmissionsCalculateResponse(
        project_id=req.project_id,
        project_stage_instance_id=req.project_stage_instance_id,
        project_option_id=req.project_option_id,
        commencement_year=commencement_year,
        operational_life_years=operational_life_years,
        interim_absolute_emissions_tco2e=interim_total_rounded,
        base_case_option_id=base_case_option_id,
        base_case_emissions_tco2e=base_case_interim_rounded,
        final_user_emissions_tco2e=final_user_emissions,
        # annual_rows=annual_rows,  # uncomment to include per-year breakdown
    )
