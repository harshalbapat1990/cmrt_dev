from decimal import Decimal
from types import SimpleNamespace

from crud.activity_data import activity_emissions_measure
from services.completeness_emissions_ledger import aggregate_completeness_facts


def _fact(**overrides):
    fact = {
        "value": Decimal("0"),
        "lifecycle_module_code": None,
        "source_category": None,
        "accounting_basis": "common",
        "reporting_measure": "actual",
        "is_supplementary": False,
        "activity_data_id": "linked-row",
        "project_option_id": "option-1",
        "activity_option_id": "option-1",
        "ui_table_key": None,
        "extra_fields": {},
    }
    fact.update(overrides)
    return fact


def test_aggregate_completeness_facts_uses_selected_electricity_basis_and_ledger_measures():
    facts = [
        _fact(value=Decimal("3"), lifecycle_module_code="A5", source_category="Materials"),
        _fact(value=Decimal("10"), lifecycle_module_code="A5", source_category="Electricity", accounting_basis="location"),
        _fact(value=Decimal("20"), lifecycle_module_code="A5", source_category="Electricity", accounting_basis="market"),
        _fact(value=Decimal("5"), lifecycle_module_code="B2-5", source_category="Waste", reporting_measure="mitigation"),
        _fact(value=Decimal("2"), reporting_measure="offset"),
        _fact(value=Decimal("4"), reporting_measure="stored_carbon"),
        _fact(value=Decimal("99"), lifecycle_module_code="A5", reporting_measure="baseline_adjustment"),
        _fact(value=Decimal("100"), lifecycle_module_code="A5", is_supplementary=True),
    ]

    location = aggregate_completeness_facts(facts, accounting_method="location")
    market = aggregate_completeness_facts(facts, accounting_method="market")

    assert location["modules"]["a5"] == Decimal("13")
    assert market["modules"]["a5"] == Decimal("23")
    assert location["modules"]["b2_b5"] == Decimal("5")
    assert location["modules"]["offsets"] == Decimal("-2")
    assert location["modules"]["stored_carbon"] == Decimal("4")
    assert location["source_categories"] == {
        "Electricity": Decimal("10"),
        "Materials": Decimal("3"),
        "Waste": Decimal("5"),
    }


def test_aggregate_completeness_facts_uses_annual_b8_and_avoids_linked_duplicate():
    facts = [
        _fact(value=Decimal("100"), lifecycle_module_code="B8", ui_table_key="roadUsers"),
        _fact(value=Decimal("40"), lifecycle_module_code="B8", ui_table_key="largeRoadParams"),
        _fact(
            value=Decimal("12"),
            lifecycle_module_code="B8",
            value_key="b8_road_light_vehicle",
            source_category="Road user transport",
            activity_data_id=None,
        ),
    ]

    result = aggregate_completeness_facts(facts)

    assert result["modules"]["b8"] == Decimal("12")
    assert result["source_categories"] == {}


def test_aggregate_completeness_facts_keeps_ledgered_b8_rows_when_annual_facts_are_absent():
    facts = [
        _fact(value=Decimal("7"), lifecycle_module_code="B8", ui_table_key="roadUsers"),
        _fact(value=Decimal("8"), lifecycle_module_code="B8", ui_table_key="railUsers"),
        _fact(
            value=Decimal("4"), lifecycle_module_code="B8", ui_table_key="largeRoadParams",
            extra_fields={"gradient": "flat", "curvature": "straight", "roughness": "low", "ev_uptake_scenario": "base"},
        ),
        _fact(
            value=Decimal("6"), lifecycle_module_code="B8", ui_table_key="largeRoadParams",
            extra_fields={"gradient": "flat", "curvature": "straight", "roughness": "low", "ev_uptake_scenario": "base"},
        ),
        _fact(
            value=Decimal("3"), lifecycle_module_code="B8", ui_table_key="largeRoadParams",
            extra_fields={"gradient": "hilly", "curvature": "curved", "roughness": "high", "ev_uptake_scenario": "base"},
        ),
    ]

    result = aggregate_completeness_facts(facts)

    assert result["modules"]["b8"] == Decimal("24")


def test_activity_row_emissions_value_uses_its_ledger_reporting_measure():
    assert activity_emissions_measure(SimpleNamespace(
        extra_fields={"emissions_category": "Offset"},
        project_mitigation_id=None,
        ui_table_key="opEnergyDetailed",
    )) == "offset"
    assert activity_emissions_measure(SimpleNamespace(
        extra_fields={},
        project_mitigation_id="mitigation-id",
        ui_table_key="component",
    )) == "mitigation"
    assert activity_emissions_measure(SimpleNamespace(
        extra_fields={},
        project_mitigation_id=None,
        ui_table_key="component",
    )) == "actual"


def test_completeness_keeps_sat4p_module_and_source_category_allocation():
    facts = [
        _fact(
            value=Decimal("11"),
            lifecycle_module_code="A1-A3",
            source_category="Materials",
            ui_table_key="shortcutSat4p",
            extra_fields={"source": "Construction materials"},
        ),
        _fact(
            value=Decimal("7"),
            lifecycle_module_code="A5",
            source_category="Fuels",
            ui_table_key="shortcutSat4p",
            extra_fields={"source": "Disposal"},
        ),
    ]

    result = aggregate_completeness_facts(facts)

    assert result["modules"]["a1_a3"] == Decimal("0")
    assert result["modules"]["a5"] == Decimal("7")
    assert result["source_categories"] == {
        "Materials": Decimal("11"),
        "Fuels": Decimal("7"),
    }
