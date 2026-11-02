from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import crud.activity_data as activity_data_crud
import services.emissions_calculator as emissions_calculator
from schemas.activity_data import ActivityDataCreate, ActivityDataUpdate


@pytest.mark.asyncio
async def test_grade34_row_uses_detailed_calculator_and_ignores_legacy_metric_key(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        ui_table_key="bcDetailedLevel",
        quantity=0,
        metric_natural_key={"emissions_source": "AAC panel (inc. reinforced)"},
        _strict_dataset_recalculation=True,
    )
    detailed_calculation = AsyncMock(return_value=Decimal("9.230379"))
    generic_metric_lookup = AsyncMock(side_effect=AssertionError("generic metric lookup must be skipped"))
    monkeypatch.setattr(
        emissions_calculator,
        "recalc_grade34_construction_activity_row",
        detailed_calculation,
    )
    monkeypatch.setattr(
        emissions_calculator,
        "get_background_grade_metric_by_natural_key",
        generic_metric_lookup,
    )

    db = object()
    result = await emissions_calculator._calculate_and_store_impl(db, row, raise_errors=True)

    assert result == Decimal("9.230379")
    assert row.metric_natural_key is None
    detailed_calculation.assert_awaited_once_with(db, row)
    generic_metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_grade34_create_discards_generic_metric_reference(monkeypatch):
    revision_id = uuid4()
    metric_lookup = AsyncMock(side_effect=AssertionError("generic metric lookup must be skipped"))
    monkeypatch.setattr(
        activity_data_crud.ProjectContextHelper,
        "fetch_project_dataset_revision",
        AsyncMock(return_value=revision_id),
    )
    monkeypatch.setattr(activity_data_crud, "get_background_grade_metric_orm", metric_lookup)
    payload = ActivityDataCreate(
        project_id=uuid4(),
        project_stage_instance_id=uuid4(),
        quantity=2000,
        ui_table_key="bcDetailedLevel",
        metric_id=uuid4(),
        metric_natural_key={"emissions_source": "AAC panel (inc. reinforced)"},
        extra_fields={"emissions_source_name": "Plasterboard"},
    )

    data = await activity_data_crud._activity_data_model_kwargs(object(), payload)

    assert data["dataset_revision_id"] == revision_id
    assert data["metric_natural_key"] is None
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_grade34_update_clears_an_existing_generic_metric_reference(monkeypatch):
    revision_id = uuid4()
    metric_lookup = AsyncMock(side_effect=AssertionError("generic metric lookup must be skipped"))
    monkeypatch.setattr(
        activity_data_crud.ProjectContextHelper,
        "fetch_project_dataset_revision",
        AsyncMock(return_value=revision_id),
    )
    monkeypatch.setattr(activity_data_crud, "get_background_grade_metric_orm", metric_lookup)
    existing_row = SimpleNamespace(
        project_id=uuid4(),
        ui_table_key="bcDetailedLevel",
        metric_natural_key={"emissions_source": "AAC panel (inc. reinforced)"},
    )

    data = await activity_data_crud._activity_data_update_kwargs(
        object(), existing_row, ActivityDataUpdate(extra_fields={"emissions_source_name": "Plasterboard"})
    )

    assert data["dataset_revision_id"] == revision_id
    assert data["metric_natural_key"] is None
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_grade34_strict_recalculation_skips_missing_required_inputs(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        ui_table_key="bcDetailedLevel",
        quantity=0,
        metric_natural_key={"emissions_source": "AAC panel (inc. reinforced)"},
        _strict_dataset_recalculation=True,
    )
    monkeypatch.setattr(
        emissions_calculator,
        "recalc_grade34_construction_activity_row",
        AsyncMock(return_value=None),
    )

    result = await emissions_calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result is None
    assert row.metric_natural_key is None
