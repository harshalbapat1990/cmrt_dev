"""
test_dataset_permissions.py
===========================
Tests for the dataset governance rules and category validation matrix
defined in core/dataset_permissions.py.
"""
from __future__ import annotations

import pytest
from core.dataset_permissions import (
    ALL_BRANCHES,
    ORG_ONLY,
    READ_ONLY,
    SUPERADMIN_ONLY,
    DATASET_RULES,
    get_dataset_category,
    is_scope_allowed,
)


def test_dataset_rules_contain_expected_datasets():
    # ALL_BRANCHES
    assert DATASET_RULES["background_grade_metrics"] == ALL_BRANCHES
    assert DATASET_RULES["default_transport_distances"] == ALL_BRANCHES
    assert DATASET_RULES["recycled_content"] == ALL_BRANCHES
    assert DATASET_RULES["material_recycled_content"] == ALL_BRANCHES
    assert DATASET_RULES["default_waste_rates"] == ALL_BRANCHES
    assert DATASET_RULES["vehicle_masses"] == ALL_BRANCHES
    assert DATASET_RULES["vepm_factors"] == ALL_BRANCHES

    # ORG_ONLY
    assert DATASET_RULES["maintenance_replacement_factors"] == ORG_ONLY
    assert DATASET_RULES["default_wastage_rate"] == ORG_ONLY
    assert DATASET_RULES["carbon_values"] == ORG_ONLY
    assert DATASET_RULES["operational_equipment"] == ORG_ONLY
    assert DATASET_RULES["freight_rail_factors"] == ORG_ONLY
    assert DATASET_RULES["ev_uptake_factors"] == ORG_ONLY
    assert DATASET_RULES["vehicle_energy_conversion_rates"] == ORG_ONLY
    assert DATASET_RULES["direct_substitutions"] == ORG_ONLY
    assert DATASET_RULES["electricity_recycling_assumptions"] == ORG_ONLY
    assert DATASET_RULES["concrete_mix_designs"] == ORG_ONLY

    # SUPERADMIN_ONLY
    assert DATASET_RULES["densities"] == SUPERADMIN_ONLY
    assert DATASET_RULES["electric_decarb_factors"] == SUPERADMIN_ONLY
    assert DATASET_RULES["unit_conversions"] == SUPERADMIN_ONLY
    assert DATASET_RULES["energy_density_conversions"] == SUPERADMIN_ONLY
    assert DATASET_RULES["renewable_energy_classification"] == SUPERADMIN_ONLY
    assert DATASET_RULES["interrupted_vehicles"] == SUPERADMIN_ONLY
    assert DATASET_RULES["uninterrupted_vehicles"] == SUPERADMIN_ONLY
    assert DATASET_RULES["fugitives"] == SUPERADMIN_ONLY

    # READ_ONLY
    assert DATASET_RULES["audit_logs"] == READ_ONLY


def test_get_dataset_category_fallback():
    assert get_dataset_category("unknown_custom_dataset") == ALL_BRANCHES
    assert get_dataset_category("DENSITIES") == SUPERADMIN_ONLY


def test_is_scope_allowed_all_branches():
    dataset = "default_transport_distances"
    assert is_scope_allowed(dataset, "DEFAULT") is True
    assert is_scope_allowed(dataset, "ORG") is True
    assert is_scope_allowed(dataset, "PROJECT") is True


def test_is_scope_allowed_org_only():
    dataset = "carbon_values"
    assert is_scope_allowed(dataset, "DEFAULT") is True
    assert is_scope_allowed(dataset, "ORG") is True
    assert is_scope_allowed(dataset, "PROJECT") is False


def test_is_scope_allowed_superadmin_only():
    dataset = "densities"
    assert is_scope_allowed(dataset, "DEFAULT") is True
    assert is_scope_allowed(dataset, "ORG") is False
    assert is_scope_allowed(dataset, "PROJECT") is False


def test_is_scope_allowed_read_only():
    dataset = "audit_logs"
    assert is_scope_allowed(dataset, "DEFAULT") is False
    assert is_scope_allowed(dataset, "ORG") is False
    assert is_scope_allowed(dataset, "PROJECT") is False
