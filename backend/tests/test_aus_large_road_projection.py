from decimal import Decimal

from services.aus_road_emissions_batch import AUS_INTENSITY_BATCH_SQL
from services.user_emissions_aus_large_road_calculations import (
    _SimpleAnchor,
    _annual_emissions_tco2e,
    _build_year_values,
    _worksheet_speed,
)


def test_large_road_projection_interpolates_and_carries_before_first_anchor():
    anchors = [
        _SimpleAnchor(2038, Decimal("11000"), Decimal("72")),
        _SimpleAnchor(2045, Decimal("13000"), Decimal("72")),
    ]

    projected = _build_year_values(anchors, [2037, 2038, 2041, 2045])

    assert projected[2037] == (Decimal("11000"), Decimal("72"))
    assert projected[2038] == (Decimal("11000"), Decimal("72"))
    assert projected[2041] == (Decimal("11857.14285714285714285714286"), Decimal("72"))
    assert projected[2045] == (Decimal("13000"), Decimal("72"))


def test_large_road_forecast_uses_least_squares_over_all_anchors():
    anchors = [
        _SimpleAnchor(2029, Decimal("1"), Decimal("10")),
        _SimpleAnchor(2030, Decimal("3"), Decimal("20")),
        _SimpleAnchor(2031, Decimal("2"), Decimal("30")),
    ]

    projected = _build_year_values(anchors, [2032])

    # Least squares across all three anchors forecasts VKT=3. Extrapolating
    # from only the last two anchors would incorrectly forecast VKT=1.
    assert projected[2032] == (Decimal("3"), Decimal("40"))


def test_large_road_projection_with_one_anchor_stays_constant():
    anchor = _SimpleAnchor(2035, Decimal("500"), Decimal("44.5"))

    assert _build_year_values([anchor], [2028, 2035, 2098]) == {
        2028: (Decimal("500"), Decimal("44.5")),
        2035: (Decimal("500"), Decimal("44.5")),
        2098: (Decimal("500"), Decimal("44.5")),
    }


def test_worksheet_speed_rounding_matches_excel_half_away_from_zero():
    assert _worksheet_speed(Decimal("44.49")) == Decimal("44")
    assert _worksheet_speed(Decimal("44.5")) == Decimal("45")
    assert _worksheet_speed(Decimal("-1.5")) == Decimal("-2")


def test_annual_emissions_uses_full_precision_and_accepts_zero_vkt():
    vkt = Decimal("123.456789123")
    intensity = Decimal("1.23456789123")

    assert _annual_emissions_tco2e(vkt, intensity) == (
        vkt * intensity / Decimal("1000000")
    )
    assert _annual_emissions_tco2e(Decimal("0"), intensity) == Decimal("0")


def test_intensity_batch_reports_revision_scoped_electricity_factor_presence():
    sql = str(AUS_INTENSITY_BATCH_SQL).lower()

    assert "has_scope2_location_factor" in sql
    assert "has_scope3_location_factor" in sql
    assert "edf.dataset_revision_id = cast(:p_dataset_revision_id as uuid)" in sql
    assert "edf.year = requested.assessment_year" in sql
    assert "gr.name = :p_state" in sql
