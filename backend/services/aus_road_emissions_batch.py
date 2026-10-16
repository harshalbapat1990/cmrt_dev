"""Shared SQL and request-shaping helpers for batched AUS road intensities."""

from typing import Iterable, Optional

from sqlalchemy import text


AUS_INTENSITY_BATCH_SQL = text("""
    SELECT requested.assessment_year,
           requested.speed_kph,
           intensity.vehicle_class,
           intensity.fleet_avg_emissions_intensity_gco2e_per_vkt
    FROM jsonb_to_recordset(CAST(:requested_pairs AS jsonb))
         AS requested(assessment_year integer, speed_kph numeric)
    CROSS JOIN LATERAL fn_veh_emissions_intensity_aus(
        requested.assessment_year, :p_state, :p_scenario,
        :p_gradient, :p_curvature, :p_iri,
        requested.speed_kph, CAST(:p_dataset_revision_id AS uuid)
    ) AS intensity
""")


def build_aus_intensity_pairs(
    years: list[int],
    speeds: list[float],
    min_year: Optional[int],
    max_year: Optional[int],
) -> list[dict[str, int | float]]:
    """Build unique year/speed function inputs, clamping years to factor coverage."""
    return build_aus_intensity_pairs_for_inputs(
        ((year, speed) for year in years for speed in speeds), min_year, max_year
    )


def build_aus_intensity_pairs_for_inputs(
    year_speed_pairs: Iterable[tuple[int, float]],
    min_year: Optional[int],
    max_year: Optional[int],
) -> list[dict[str, int | float]]:
    """Clamp and deduplicate only the year/speed pairs actually requested."""
    pairs: set[tuple[int, float]] = set()
    for year, speed in year_speed_pairs:
        lookup_year = year
        if max_year is not None and lookup_year > max_year:
            lookup_year = max_year
        if min_year is not None and lookup_year < min_year:
            lookup_year = min_year
        pairs.add((lookup_year, float(speed)))
    return [
        {"assessment_year": year, "speed_kph": speed}
        for year, speed in sorted(pairs)
    ]
