from __future__ import annotations

from typing import Optional

# Permission category constants
ALL_BRANCHES = "ALL_BRANCHES"
ORG_ONLY = "ORG_ONLY"
SUPERADMIN_ONLY = "SUPERADMIN_ONLY"
READ_ONLY = "READ_ONLY"

VALID_PERMISSION_CATEGORIES = {
    ALL_BRANCHES,
    ORG_ONLY,
    SUPERADMIN_ONLY,
    READ_ONLY,
}

# Single source of truth for dataset governance rules
DATASET_RULES: dict[str, str] = {
    # ALL_BRANCHES: Default (SUPER_ADMIN), Org (ORG_ADMIN), Project (PROJECT_ADMIN/EDITOR)
    "background_grade_metrics": ALL_BRANCHES,
    "grade_1_asset_level": ALL_BRANCHES,
    "grade_2_component_level": ALL_BRANCHES,
    "grade_3_4_detailed_level": ALL_BRANCHES,
    "default_transport_distances": ALL_BRANCHES,
    "transport": ALL_BRANCHES,
    "recycled_content": ALL_BRANCHES,
    "recycled_content_factors": ALL_BRANCHES,
    "material_recycled_content": ALL_BRANCHES,
    "default_waste_rates": ALL_BRANCHES,
    "waste_rates": ALL_BRANCHES,
    "vehicle_masses": ALL_BRANCHES,
    "vepm_tables": ALL_BRANCHES,
    "vepm_factors": ALL_BRANCHES,

    # ORG_ONLY: Default (SUPER_ADMIN), Org (ORG_ADMIN), Project (NOT ALLOWED)
    "maintenance_replacement": ORG_ONLY,
    "maintenance_replacement_factors": ORG_ONLY,
    "wastage_rates": ORG_ONLY,
    "default_wastage_rate": ORG_ONLY,
    "bau_assumptions": ORG_ONLY,
    "concrete_mix_assumptions": ORG_ONLY,
    "carbon_values": ORG_ONLY,
    "operational_equipment": ORG_ONLY,
    "freight_rail": ORG_ONLY,
    "freight_rail_factors": ORG_ONLY,
    "ev_uptake": ORG_ONLY,
    "ev_uptake_factors": ORG_ONLY,
    "vehicle_energy": ORG_ONLY,
    "vehicle_energy_conversion_rates": ORG_ONLY,
    "direct_substitutions": ORG_ONLY,
    "electricity_recycling_assumptions": ORG_ONLY,
    "concrete_mix_designs": ORG_ONLY,

    # SUPERADMIN_ONLY: Default (SUPER_ADMIN), Org (NOT ALLOWED), Project (NOT ALLOWED)
    "densities": SUPERADMIN_ONLY,
    "electric_decarb_factors": SUPERADMIN_ONLY,
    "electricity_decarbonisation": SUPERADMIN_ONLY,
    "unit_conversions": SUPERADMIN_ONLY,
    "energy_density_conversions": SUPERADMIN_ONLY,
    "renewable_energy_classification": SUPERADMIN_ONLY,
    "renewable_energy": SUPERADMIN_ONLY,
    "interrupted_vehicles": SUPERADMIN_ONLY,
    "user_enabled_carbon_stop_start": SUPERADMIN_ONLY,
    "uninterrupted_vehicles": SUPERADMIN_ONLY,
    "user_enabled_carbon_uninterrupted": SUPERADMIN_ONLY,
    "fugitives": SUPERADMIN_ONLY,

    # READ_ONLY: Immutable
    "audit_trail": READ_ONLY,
    "audit_logs": READ_ONLY,
}


def get_dataset_category(dataset_type: str) -> str:
    """Return the governance category for a dataset key, defaulting to ALL_BRANCHES."""
    return DATASET_RULES.get(dataset_type.lower(), ALL_BRANCHES)


def is_scope_allowed(dataset_type: str, scope_type: str) -> bool:
    """
    Check whether a dataset category is permitted to be edited at a given revision scope tier.

    Scope tiers:
      - DEFAULT: allowed for ALL_BRANCHES, ORG_ONLY, SUPERADMIN_ONLY
      - ORG:     allowed for ALL_BRANCHES, ORG_ONLY
      - PROJECT: allowed for ALL_BRANCHES only
    """
    category = get_dataset_category(dataset_type)
    norm_scope = (scope_type or "").upper()

    if category == READ_ONLY:
        return False
    if category == SUPERADMIN_ONLY:
        return norm_scope == "DEFAULT"
    if category == ORG_ONLY:
        return norm_scope in ("DEFAULT", "ORG")
    if category == ALL_BRANCHES:
        return norm_scope in ("DEFAULT", "ORG", "PROJECT")

    return False
