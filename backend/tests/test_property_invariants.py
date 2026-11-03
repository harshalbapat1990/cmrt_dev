"""Property checks for pure normalization and projection functions."""

from decimal import Decimal

from hypothesis import given, settings, strategies as st

from schemas.partner_organizations import normalize_partner_name
from services.user_emissions_aus_large_road_calculations import (
    _SimpleAnchor,
    _build_year_values,
)


@settings(max_examples=100, deadline=None)
@given(st.text(min_size=1).filter(lambda value: bool(value.split())))
def test_partner_name_normalization_is_idempotent(name: str):
    normalized = normalize_partner_name(name)

    assert normalized == normalize_partner_name(normalized)
    assert normalized == normalize_partner_name(f"  {name}  ")
    assert normalized == normalized.strip()


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=1900, max_value=2200),
            st.decimals(min_value="0", max_value="1000000", places=3),
            st.decimals(min_value="1", max_value="150", places=2),
        ),
        min_size=1,
        max_size=8,
        unique_by=lambda item: item[0],
    ),
    st.integers(min_value=1900, max_value=2200),
)
def test_large_road_projection_returns_requested_year_and_finite_values(anchors, year):
    parsed_anchors = [
        _SimpleAnchor(year=anchor_year, vkt=Decimal(vkt), average_speed_kph=Decimal(speed))
        for anchor_year, vkt, speed in anchors
    ]
    projected = _build_year_values(parsed_anchors, [year])

    assert list(projected) == [year]
    assert all(value.is_finite() for value in projected[year])

