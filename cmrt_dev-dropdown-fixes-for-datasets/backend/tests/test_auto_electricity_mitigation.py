"""Unit tests for electricity auto-mitigation helpers."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from crud.electricity_recycling_assumptions import ELECTRICITY_ERA_SOURCE_MAP
from services.auto_electricity_mitigation import (
    AUTO_ELECTRICITY_LINK_KEY,
    RENEWABLE_SOURCES,
    _bucket_key,
    _has_renewable_trigger,
    _resolve_dataset_revision_id,
    build_replaced_rows,
    consolidate_adopted_rows,
    electricity_lifecycle_meta,
    sync_auto_electricity_for_table,
    year_electricity_totals,
)
from services.electricity_activity_emissions import (
    electricity_base_table_key,
    is_electricity_activity_row,
)
from models.project import ProjectClass
from models.project_stage_instances import ProjectStage


def _row(
    *,
    source: str,
    year: int,
    qty: float,
    mitigation_id: str | None = None,
    period_id=None,
):
    extra = {
        "emission_source": source,
        "year": year,
        "quantity_mwh": qty,
    }
    if mitigation_id:
        extra[AUTO_ELECTRICITY_LINK_KEY] = mitigation_id
    return SimpleNamespace(
        extra_fields=extra,
        quantity=Decimal(str(qty)),
        submission_period_id=period_id,
    )


class TestConsolidateAdoptedRows:
    def test_sums_same_source_and_year(self):
        rows = [
            _row(source="Onsite Renewable Electricity", year=2030, qty=100),
            _row(source="Onsite Renewable Electricity", year=2030, qty=50),
            _row(source="Grid Electricity", year=2030, qty=200),
            _row(source="Onsite Renewable Electricity", year=2031, qty=10),
        ]
        out = consolidate_adopted_rows(rows)
        by_key = {(r["emission_source"], r["year"]): r["quantity_mwh"] for r in out}
        assert by_key[("Onsite Renewable Electricity", 2030)] == 150.0
        assert by_key[("Grid Electricity", 2030)] == 200.0
        assert by_key[("Onsite Renewable Electricity", 2031)] == 10.0


class TestBuildReplacedRows:
    def test_total_year_times_bau_pct(self):
        # Excel-style example: total 3365 MWh in 2030
        rows = [
            _row(source="Grid Electricity", year=2030, qty=1000),
            _row(source="Onsite Renewable Electricity", year=2030, qty=1365),
            _row(source="Offsite Renewable Electricity", year=2030, qty=1000),
        ]
        era = {
            "Grid Electricity": Decimal("0.50"),
            "Onsite Renewable Electricity": Decimal("0.30"),
            "Offsite Renewable Electricity": Decimal("0.20"),
        }
        out = build_replaced_rows(rows, era)
        by_source = {r["emission_source"]: r["quantity_mwh"] for r in out if r["year"] == 2030}
        assert by_source["Grid Electricity"] == pytest.approx(1682.5)
        assert by_source["Onsite Renewable Electricity"] == pytest.approx(1009.5)
        assert by_source["Offsite Renewable Electricity"] == pytest.approx(673.0)

    def test_user_example_year_totals_redistributed_by_bau(self):
        rows = [
            _row(source="Grid Electricity", year=2028, qty=464),
            _row(source="Grid Electricity", year=2029, qty=500),
            _row(source="Grid Electricity", year=2030, qty=804),
            _row(source="Onsite Renewable Electricity", year=2028, qty=400),
            _row(source="Onsite Renewable Electricity", year=2029, qty=575),
            _row(source="Onsite Renewable Electricity", year=2030, qty=1079),
            _row(source="Offsite Renewable Electricity", year=2028, qty=400),
            _row(source="Offsite Renewable Electricity", year=2029, qty=521),
            _row(source="Offsite Renewable Electricity", year=2030, qty=1482),
        ]
        era = {
            "Grid Electricity": Decimal("0.55"),
            "Onsite Renewable Electricity": Decimal("0.20"),
            "Offsite Renewable Electricity": Decimal("0.25"),
        }
        totals = year_electricity_totals(rows)
        assert totals[2028] == Decimal("1264")
        assert totals[2029] == Decimal("1596")
        assert totals[2030] == Decimal("3365")

        out = build_replaced_rows(rows, era)
        by_year_source = {
            (r["year"], r["emission_source"]): r["quantity_mwh"] for r in out
        }
        assert by_year_source[(2028, "Grid Electricity")] == pytest.approx(1264 * 0.55)
        assert by_year_source[(2028, "Onsite Renewable Electricity")] == pytest.approx(1264 * 0.20)
        assert by_year_source[(2028, "Offsite Renewable Electricity")] == pytest.approx(1264 * 0.25)
        assert by_year_source[(2030, "Grid Electricity")] == pytest.approx(3365 * 0.55)

    def test_year_total_redistributed_by_era_bau_pcts(self):
        """1100 MWh in one year × ERA BAU % (25 / 30 / 45) for Sources Replaced."""
        rows = [
            _row(source="Onsite Renewable Electricity", year=2029, qty=600),
            _row(source="Onsite Renewable Electricity", year=2029, qty=500),
        ]
        era = {
            "Grid Electricity": Decimal("0.45"),
            "Onsite Renewable Electricity": Decimal("0.25"),
            "Offsite Renewable Electricity": Decimal("0.30"),
        }
        assert year_electricity_totals(rows)[2029] == Decimal("1100")

        out = build_replaced_rows(rows, era)
        by_source = {r["emission_source"]: r["quantity_mwh"] for r in out if r["year"] == 2029}
        assert by_source["Offsite Renewable Electricity"] == pytest.approx(330.0)
        assert by_source["Grid Electricity"] == pytest.approx(495.0)
        assert by_source["Onsite Renewable Electricity"] == pytest.approx(275.0)

    def test_drops_year_when_all_source_rows_for_year_removed(self):
        rows = [
            _row(source="Onsite Renewable Electricity", year=2029, qty=575),
            _row(source="Grid Electricity", year=2029, qty=500),
        ]
        era = {
            "Grid Electricity": Decimal("0.55"),
            "Onsite Renewable Electricity": Decimal("0.20"),
            "Offsite Renewable Electricity": Decimal("0.25"),
        }
        adopted = consolidate_adopted_rows(rows)
        replaced = build_replaced_rows(rows, era)
        assert all(r["year"] != 2028 for r in adopted)
        assert all(r["year"] != 2028 for r in replaced)
        assert {r["year"] for r in adopted} == {2029}


class TestTriggerRule:
    def test_renewable_sources_trigger(self):
        assert _has_renewable_trigger([_row(source="Onsite Renewable Electricity", year=2030, qty=1)])
        assert _has_renewable_trigger([_row(source="Offsite Renewable Electricity", year=2030, qty=1)])

    def test_grid_only_does_not_trigger(self):
        assert not _has_renewable_trigger([_row(source="Grid Electricity", year=2030, qty=1000)])

    def test_zero_qty_renewable_does_not_trigger(self):
        assert not _has_renewable_trigger(
            [_row(source="Onsite Renewable Electricity", year=2030, qty=0)]
        )

    def test_empty_does_not_trigger(self):
        assert not _has_renewable_trigger([])


class TestEraMapping:
    def test_construction_metric_codes(self):
        m = ELECTRICITY_ERA_SOURCE_MAP["electricity"]
        assert m["Onsite Renewable Electricity"] == "onsite_renewable_construction"
        assert m["Offsite Renewable Electricity"] == "offsite_renewable_construction"
        assert m["Grid Electricity"] == "grid_electricity_construction"

    def test_operation_metric_codes(self):
        m = ELECTRICITY_ERA_SOURCE_MAP["opEnergyElectricity"]
        assert m["Onsite Renewable Electricity"] == "onsite_renewable_operation"
        assert m["Offsite Renewable Electricity"] == "offsite_renewable_operation"
        assert m["Grid Electricity"] == "grid_electricity_operation"


class TestLifecycleMeta:
    def test_table_keys(self):
        assert electricity_lifecycle_meta("electricity") == ("construction", "Construction")
        assert electricity_lifecycle_meta("opEnergyElectricity") == (
            "operations_maintenance",
            "Operations & Maintenance",
        )


class TestElectricityActivityEmissionsKeys:
    def test_base_and_suffixed_keys(self):
        assert electricity_base_table_key("electricity") == "electricity"
        assert electricity_base_table_key("opEnergyElectricity") == "opEnergyElectricity"
        assert electricity_base_table_key("electricity-mitigation-subst-adopted") == "electricity"
        assert electricity_base_table_key("opEnergyElectricity-mitigation-subst-replaced") == "opEnergyElectricity"
        assert electricity_base_table_key("constructionG3") is None

    def test_is_electricity_activity_row(self):
        row = SimpleNamespace(ui_table_key="electricity-mitigation-subst-adopted")
        assert is_electricity_activity_row(row)


class TestConstructionPeriodScope:
    def test_distinct_bucket_keys_per_period(self):
        p1, p2 = uuid4(), uuid4()
        assert _bucket_key(uuid4(), p1) != _bucket_key(uuid4(), p2)


@pytest.mark.asyncio
async def test_resolve_dataset_revision_falls_back_to_published():
    published_id = uuid4()
    project_id = uuid4()
    db = AsyncMock()

    with patch(
        "services.auto_electricity_mitigation.list_project_dataset_revisions_by_project",
        new=AsyncMock(return_value=[]),
    ), patch(
        "services.auto_electricity_mitigation.get_published_dataset_revision",
        new=AsyncMock(return_value=SimpleNamespace(id=published_id)),
    ):
        result = await _resolve_dataset_revision_id(db, project_id, [])

    assert result == published_id


@pytest.mark.asyncio
async def test_sync_deletes_mitigation_when_all_source_rows_removed():
    """Deleting the last source row should remove the linked auto mitigation."""
    mitigation_id = uuid4()
    project_id = uuid4()
    stage_instance = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        stage=ProjectStage.DESIGN,
    )
    project = SimpleNamespace(id=project_id, project_class=ProjectClass.LARGE)

    db = AsyncMock()

    with patch(
        "services.auto_electricity_mitigation._load_source_rows",
        new=AsyncMock(return_value=[]),
    ), patch(
        "services.auto_electricity_mitigation.delete_project_mitigation",
        new=AsyncMock(),
    ) as mock_delete, patch(
        "services.auto_electricity_mitigation._clear_links_on_sources",
        new=AsyncMock(),
    ):
        await sync_auto_electricity_for_table(
            db,
            stage_instance,
            "electricity",
            uuid4(),
            None,
            project=project,
            known_mitigation_id=mitigation_id,
        )

    mock_delete.assert_awaited_once_with(db, mitigation_id)


@pytest.mark.asyncio
async def test_sync_deletes_mitigation_when_no_renewable_rows():
    """Removing all renewable rows should delete the linked mitigation."""
    mitigation_id = uuid4()
    project_id = uuid4()
    stage_instance = SimpleNamespace(
        id=uuid4(),
        project_id=project_id,
        stage=ProjectStage.DESIGN,
    )
    project = SimpleNamespace(id=project_id, project_class=ProjectClass.LARGE)
    source_rows = [
        _row(source="Grid Electricity", year=2030, qty=500, mitigation_id=str(mitigation_id)),
    ]

    db = AsyncMock()

    with patch(
        "services.auto_electricity_mitigation._load_source_rows",
        new=AsyncMock(return_value=source_rows),
    ), patch(
        "services.auto_electricity_mitigation.delete_project_mitigation",
        new=AsyncMock(),
    ) as mock_delete, patch(
        "services.auto_electricity_mitigation._clear_links_on_sources",
        new=AsyncMock(),
    ) as mock_clear:
        await sync_auto_electricity_for_table(
            db,
            stage_instance,
            "electricity",
            uuid4(),
            None,
            project=project,
        )

    mock_delete.assert_awaited_once_with(db, mitigation_id)
    mock_clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_skips_non_large_projects():
    db = AsyncMock()
    stage_instance = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        stage=ProjectStage.DESIGN,
    )
    project = SimpleNamespace(id=stage_instance.project_id, project_class=ProjectClass.SMALL)

    with patch(
        "services.auto_electricity_mitigation._load_source_rows",
        new=AsyncMock(),
    ) as mock_load:
        await sync_auto_electricity_for_table(
            db,
            stage_instance,
            "electricity",
            uuid4(),
            None,
            project=project,
        )

    mock_load.assert_not_awaited()
