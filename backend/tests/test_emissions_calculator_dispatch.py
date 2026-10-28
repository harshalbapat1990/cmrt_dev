from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import services.emissions_calculator as calculator


SPECIALIZED_KEYS = [
    "component",
    "constructionG2",
    "componentRepl",
    "replDetailed",
    "opEnergy",
    "opEnergyDetailed",
    "shortcutIsMaterials",
    "useB1G2",
    "useB1G3",
    "concreteRegSimplified",
    "concreteRegDetailed",
    "electricity",
    "opEnergyElectricity",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("table_key", [
    "bcDetailedLevel",
    "constructionG3",
    "recurringG3",
    "constructionG3-mitigation-subst-replaced",
])
async def test_grade34_tables_use_their_detailed_calculator_with_any_metric_key(monkeypatch, table_key):
    detailed_calculation = AsyncMock(return_value=Decimal("9.230379"))
    metric_lookup = AsyncMock(side_effect=AssertionError("Grade 3/4 rows must use detailed lookup"))
    monkeypatch.setattr(calculator, "recalc_grade34_construction_activity_row", detailed_calculation)
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(),
        ui_table_key=table_key,
        metric_natural_key={"grade_id": 3, "unit_id": str(uuid4())},
        _strict_dataset_recalculation=False,
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("9.230379")
    assert row.metric_natural_key is None
    detailed_calculation.assert_awaited_once()
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("base_key", SPECIALIZED_KEYS)
@pytest.mark.parametrize("metric_key", [None, {"grade_id": 2, "unit_id": str(uuid4())}])
async def test_specialized_dispatch_precedes_metric_lookup(monkeypatch, base_key, metric_key):
    handler = AsyncMock(return_value=Decimal("12.5"))
    monkeypatch.setitem(calculator._SPECIALIZED_CALCULATORS, base_key, handler)
    metric_lookup = AsyncMock(side_effect=AssertionError("specialized rows must skip generic metric lookup"))
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)
    monkeypatch.setattr(calculator, "get_background_grade_metric_orm", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(),
        ui_table_key=base_key,
        metric_natural_key=metric_key,
        metric_id=None,
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("12.5")
    handler.assert_awaited_once()
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("ui_table_key,base_key", [
    ("component-mitigation", "component"),
    ("constructionG2-mitigation-subst-adopted", "constructionG2"),
    ("componentRepl-mitigation-subst-replaced", "componentRepl"),
    ("opEnergyDetailed-mitigation", "opEnergyDetailed"),
])
async def test_mitigation_table_keys_use_the_base_specialized_calculator(monkeypatch, ui_table_key, base_key):
    handler = AsyncMock(return_value=Decimal("3.25"))
    monkeypatch.setitem(calculator._SPECIALIZED_CALCULATORS, base_key, handler)
    metric_lookup = AsyncMock(side_effect=AssertionError("mitigation rows must use specialized dispatch"))
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(id=uuid4(), ui_table_key=ui_table_key, metric_natural_key={"grade_id": 2})
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("3.25")
    handler.assert_awaited_once()
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_specialized_missing_result_does_not_fall_through_to_resolved_metric(monkeypatch):
    handler = AsyncMock(return_value=None)
    monkeypatch.setitem(calculator._SPECIALIZED_CALCULATORS, "component", handler)
    metric_lookup = AsyncMock(side_effect=AssertionError("must not use generic result"))
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(), ui_table_key="component", metric_natural_key={"grade_id": 2}, metric_id=None
    )
    assert await calculator._calculate_and_store_impl(object(), row, raise_errors=True) is None
    handler.assert_awaited_once()
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("table_key", ["roadUsers", "largeRoadUsers", "largeRoadParams"])
async def test_road_user_workflow_rows_never_enter_generic_metric_path(monkeypatch, table_key):
    metric_lookup = AsyncMock(side_effect=AssertionError("road users have an independent calculation flow"))
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(), ui_table_key=table_key, metric_natural_key={"grade_id": 1}, metric_id=None
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result is None
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("table_key", ["railUsers", "largeRailUsers"])
async def test_rail_rows_with_incomplete_inputs_do_not_use_generic_metric(monkeypatch, table_key):
    metric_lookup = AsyncMock(side_effect=AssertionError("rail user rows have a dedicated workflow"))
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(), ui_table_key=table_key, metric_natural_key={"grade_id": 1}, extra_fields={}
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result is None
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_refurbishment_uses_its_dedicated_calculator_before_metric_lookup(monkeypatch):
    handler = AsyncMock(return_value=Decimal("4.5"))
    metric_lookup = AsyncMock(side_effect=AssertionError("refurbishment must skip generic lookup"))
    monkeypatch.setattr(calculator, "_recalc_refurbishment_row", handler)
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)

    row = SimpleNamespace(
        id=uuid4(), ui_table_key="refurbishment-mitigation", metric_natural_key={"grade_id": 2}
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("4.5")
    handler.assert_awaited_once()
    metric_lookup.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("metric_key", [None, {"grade_id": 1, "typecast_id": str(uuid4())}])
async def test_grade1_asset_dispatch_uses_multistage_calculator(monkeypatch, metric_key):
    asset_handler = AsyncMock(return_value=Decimal("24322.5"))
    generic_lookup = AsyncMock(side_effect=AssertionError("assets must not multiply the generic metric"))
    monkeypatch.setattr(calculator, "recalc_asset_row", asset_handler)
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", generic_lookup)

    row = SimpleNamespace(
        id=uuid4(), ui_table_key="asset", metric_natural_key=metric_key, metric_id=None
    )
    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("24322.5")
    asset_handler.assert_awaited_once()
    generic_lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_specialized_result_does_not_mirror_optimistic_fields_to_ledger(monkeypatch):
    persist_legacy = AsyncMock()
    monkeypatch.setattr(calculator, "_calculate_and_store_impl", AsyncMock(return_value=None))
    import services.result_ledger as result_ledger

    monkeypatch.setattr(result_ledger, "persist_legacy_outputs", persist_legacy)
    db = SimpleNamespace(
        execute=AsyncMock(),
        in_transaction=lambda: True,
    )
    row = SimpleNamespace(id=uuid4(), ui_table_key="asset", extra_fields={"total_emissions_tco2e": "68550"})

    result = await calculator.calculate_and_store(db, row)

    assert result is None
    persist_legacy.assert_not_awaited()


@pytest.mark.asyncio
async def test_generic_metric_table_keeps_quantity_times_factor_behavior(monkeypatch):
    metric = SimpleNamespace(
        id=uuid4(), value=Decimal("0.000457"), unit_id=None, lifecycle_module_code="A1-A3"
    )
    metric_lookup = AsyncMock(return_value=metric)
    upsert = AsyncMock()
    monkeypatch.setattr(calculator, "get_background_grade_metric_by_natural_key", metric_lookup)
    monkeypatch.setattr(calculator, "upsert_result", upsert)
    row = SimpleNamespace(
        id=uuid4(),
        ui_table_key="genericMetricTable",
        metric_natural_key={"grade_id": 1},
        metric_id=None,
        quantity=Decimal("150000000"),
        unit_id=None,
        dataset_revision_id=uuid4(),
        project_id=uuid4(),
        project_stage_instance_id=uuid4(),
    )

    result = await calculator._calculate_and_store_impl(object(), row, raise_errors=True)

    assert result == Decimal("68550.000000000")
    upsert.assert_awaited_once()
    assert upsert.await_args.kwargs["value"] == result

