"""User-facing labels for dataset recalculation diagnostics."""

from __future__ import annotations

from typing import Any

from models.project_stage_instances import ProjectStageInstance


_STAGE_LABELS = {
    "BUSINESS_CASE": "Business case",
    "DESIGN": "Design",
    "CONSTRUCTION": "Construction",
    "RECURRING": "Recurring",
}

_ENTRY_TABLE_LABELS = {
    "asset": ("Construction", "Asset level"),
    "component": ("Construction", "Component level"),
    "componentRepl": ("Replacement and Refurbishment", "Component level replacement"),
    "refurbishment": ("Replacement and Refurbishment", "Other partial replacement or refurbishment activities"),
    "replDetailed": ("Replacement and Refurbishment", "Detailed level"),
    "constructionG2": ("Construction", "Component level (Grade 2)"),
    "constructionG3": ("Construction", "Detailed level (Grade 3)"),
    "bcDetailedLevel": ("Construction", "Detailed level (Grade 3)"),
    "electricity": ("Construction", "Electricity"),
    "opEnergy": ("Operational energy (B6)", "Operational energy"),
    "opEnergyDetailed": ("Operational energy (B6)", "Operational energy (detailed)"),
    "opEnergyElectricity": ("Operational energy (B6)", "Electricity"),
    "useB1G2": ("Use (B1)", "Component level (Grade 2)"),
    "useB1G3": ("Use (B1)", "Detailed level (Grade 3)"),
    "roadUsers": ("Users (B8)", "Road users"),
    "largeRoadUsers": ("Users (B8)", "Large road users"),
    "largeRoadParams": ("Users (B8)", "Large road user assumptions"),
    "railUsers": ("Users (B8)", "Rail users"),
    "largeRailUsers": ("Users (B8)", "Large rail users"),
    "concreteRegSimplified": ("Construction", "Concrete register (Grade 3) - simplified"),
    "concreteRegDetailed": ("Construction", "Concrete register (Grade 3) - detailed"),
    "recurringG3": ("Recurring", "Detailed level (Grade 3)"),
}

_DATASET_LABELS = {
    "v_grade34_detailed_level": "Emission Factors (Grade 3/4)",
    "Grade 3/4 detailed level factors": "Emission Factors (Grade 3/4)",
    "Grade 3/4 detailed level": "Emission Factors (Grade 3/4)",
    "Grade 2 component factors": "Emission Factors (Grade 2)",
    "Grade 2 construction factors": "Emission Factors (Grade 2)",
    "Grade 2 replacement factors": "Emission Factors (Grade 2)",
    "Background grade metrics": "Emission Factors (Grade 1)",
    "Background grade metrics / asset factors": "Emission Factors (Grade 1)",
    "Background grade metrics and related factor tables": "Emission Factors",
    # The road calculation combines several tabs, so a single missing-input
    # warning cannot claim that every individual tab is missing data. Use the
    # visible Datasets page groups instead of presenting its whole dependency list.
    "Australian road emission factors": "User emissions data / Emission Factors",
    "VEPM factors": "VEPM",
    "Rail user-emissions factors": "Freight Rail",
    "Grade 1 asset factors": "Emission Factors (Grade 1)",
    "Detailed level maintenance factors": "Maintenance & Replacement",
    "Fugitive equipment factors": "Fugitives",
    "Operational equipment factors": "Operational Equipment",
    "Operational fuel and water factors": "Operational Equipment",
    "Unit conversions": "Unit Conversions",
    "Maintenance replacement factors": "Maintenance & Replacement",
    "Electricity detailed factors": "Electricity",
    "Concrete mix and emissions factor tables": "Default concrete mix designs and Emission Factors",
}


def dataset_table_display_name(name: str) -> str:
    """Translate internal factor/view names into labels users see in Datasets."""
    return _DATASET_LABELS.get(name, name)


async def data_entry_table_display_name(db: Any, activity_row: Any) -> str:
    """Format a row's stage, data-entry substage, and visible table name."""
    raw_key = str(getattr(activity_row, "ui_table_key", "") or "")
    base_key = raw_key.split("-mitigation", 1)[0]
    substage, table_label = _ENTRY_TABLE_LABELS.get(
        base_key,
        ("Data entry", base_key.replace("_", " ").strip().title() or "Table"),
    )

    stage_label = "Stage"
    stage_instance_id = getattr(activity_row, "project_stage_instance_id", None)
    if stage_instance_id is not None:
        stage_instance = await db.get(ProjectStageInstance, stage_instance_id)
        if stage_instance is not None:
            stage_value = getattr(stage_instance.stage, "value", stage_instance.stage)
            stage_label = _STAGE_LABELS.get(str(stage_value), str(stage_value).replace("_", " ").title())

    suffix = raw_key[len(base_key):]
    if suffix == "-mitigation-subst-replaced":
        table_label += " - mitigation (replaced)"
    elif suffix == "-mitigation-subst-adopted":
        table_label += " - mitigation (adopted)"
    elif suffix.startswith("-mitigation"):
        table_label += " - mitigation"

    return f"{stage_label}-{substage}-{table_label}"
