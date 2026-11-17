from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from models.project_stage_instances import ProjectStage
from services import electricity_activity_emissions as electricity_service


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, *values):
        self.values = list(values)
        self.calls = 0

    async def execute(self, _query):
        value = self.values[self.calls]
        self.calls += 1
        return _ScalarResult(value)


@pytest.mark.asyncio
async def test_recurring_electricity_calculation_year_comes_from_selected_period(monkeypatch):
    project_id, stage_id, period_id, row_id = (uuid4() for _ in range(4))
    db = _Session(ProjectStage.RECURRING, date(2035, 7, 1))
    project = SimpleNamespace(construction_start_date=None, construction_end_date=None)
    monkeypatch.setattr(electricity_service.ProjectContextHelper, "fetch_project", lambda *_: _async_value(project))
    requested = {}

    async def calculate(_db, request):
        requested["year"] = request.year
        return SimpleNamespace(
            location_based_total_tco2e=12.5,
            market_based_total_tco2e=13.0,
            scope2_location_based_tco2e=12.0,
            scope2_market_based_tco2e=12.5,
            scope3_location_based_tco2e=0.5,
            scope3_market_based_tco2e=0.5,
        )

    async def update(_db, _row_id, patch):
        row.extra_fields = patch.extra_fields

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(electricity_service._calculator, "calculate", calculate)
    monkeypatch.setattr(electricity_service, "update_activity_data", update)
    monkeypatch.setattr(electricity_service, "upsert_result", no_op)
    row = SimpleNamespace(
        id=row_id,
        project_id=project_id,
        project_stage_instance_id=stage_id,
        submission_period_id=period_id,
        ui_table_key="electricity",
        extra_fields={"emission_source": "Grid Electricity", "quantity_mwh": "25", "unit_display": "MWh"},
        quantity=25,
        lifecycle_module_code="A5",
        dataset_revision_id=uuid4(),
        project_option_id=None,
        unit_id=None,
    )

    result = await electricity_service.recalc_electricity_activity_row(db, row)

    assert requested["year"] == 2035
    assert row.extra_fields["year"] == 2035
    assert result is not None and float(result) == 12.5


async def _async_value(value):
    return value
