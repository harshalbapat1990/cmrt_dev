from services.aus_road_emissions_batch import (
    AUS_INTENSITY_BATCH_SQL,
    build_aus_intensity_pairs,
    build_aus_intensity_pairs_for_inputs,
)


def test_build_intensity_pairs_clamps_years_and_deduplicates_speeds():
    pairs = build_aus_intensity_pairs(
        years=[2024, 2025, 2052],
        speeds=[60.0, 70.0, 60.0],
        min_year=2025,
        max_year=2050,
    )

    assert pairs == [
        {"assessment_year": 2025, "speed_kph": 60.0},
        {"assessment_year": 2025, "speed_kph": 70.0},
        {"assessment_year": 2050, "speed_kph": 60.0},
        {"assessment_year": 2050, "speed_kph": 70.0},
    ]


def test_build_intensity_pairs_preserves_years_when_factor_range_is_unknown():
    assert build_aus_intensity_pairs([2024, 2025], [55.5], None, None) == [
        {"assessment_year": 2024, "speed_kph": 55.5},
        {"assessment_year": 2025, "speed_kph": 55.5},
    ]
    assert build_aus_intensity_pairs([2024, 2025], [], None, None) == []


def test_build_intensity_pairs_for_inputs_does_not_create_unused_combinations():
    assert build_aus_intensity_pairs_for_inputs(
        [(2030, 45.0), (2031, 43.0), (2030, 45.0)], 2025, 2050
    ) == [
        {"assessment_year": 2030, "speed_kph": 45.0},
        {"assessment_year": 2031, "speed_kph": 43.0},
    ]


def test_intensity_query_batches_pairs_and_invokes_revision_scoped_function():
    sql = str(AUS_INTENSITY_BATCH_SQL).lower()

    assert "jsonb_to_recordset" in sql
    assert "cross join lateral fn_veh_emissions_intensity_aus" in sql
    assert "cast(:p_dataset_revision_id as uuid)" in sql
