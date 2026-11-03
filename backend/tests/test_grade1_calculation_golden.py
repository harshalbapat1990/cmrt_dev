"""Golden Grade 1 example independently calculated from the ECD lookup inputs."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from services.grade1_asset_calculations import (
    Grade1AssetCalculator,
    Grade1CalculationRequest,
)


@pytest.mark.asyncio
async def test_road_capex_mid_golden_example_matches_ecd_stage_breakdown(monkeypatch):
    fixture_path = Path(__file__).parent / "fixtures" / "grade1_ecd_road_mid.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    lookup = {"Source": fixture["source"], **fixture["lookup_data"]}
    monkeypatch.setattr(
        Grade1AssetCalculator,
        "_fetch_lookup_data",
        AsyncMock(return_value=lookup),
    )

    result = await Grade1AssetCalculator().calculate(
        object(),
        Grade1CalculationRequest(**fixture["inputs"]),
    )

    expected = fixture["expected_tco2e"]
    tolerance = fixture["tolerance"]
    assert result.product_stage_a1a3 == pytest.approx(expected["A1-A3"], abs=tolerance)
    assert result.transport_a4 == pytest.approx(expected["A4"], abs=tolerance)
    assert result.construction_a5 == pytest.approx(expected["A5"], abs=tolerance)
    assert result.total_emissions_tco2e == pytest.approx(expected["total"], abs=tolerance)
