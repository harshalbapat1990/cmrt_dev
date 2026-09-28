"""Ledger-backed totals used by the Completeness emissions report."""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_data import ActivityData
from models.emissions_results import EmissionsResult


_ACCOUNTING_BASES = {
    "location": ("common", "location"),
    "market": ("common", "market"),
}
_MODULE_FIELDS = {
    "A1-A3": "a1_a3",
    "A4": "a4",
    "A5": "a5",
    "B1": "b1",
    "B2-5": "b2_b5",
    "B6": "b6",
    "B7": "b7",
    "B8": "b8",
}
_SOURCE_CATEGORY_TABLE_KEYS = {
    "bcDetailedLevel", "constructionG3", "recurringG3", "useB1G3",
    "replDetailed", "opEnergyDetailed", "component", "componentRepl",
    "useB1G2", "asset", "concreteRegSimplified", "concreteRegDetailed",
    "refurbishment", "electricity", "opEnergyElectricity", "opEnergy",
    "shortcutIsMaterials", "shortcutSat4p",
}
_A5_SAT4P_SOURCES = {
    "Construction processes/equipment", "Disposal", "Transport off-site (waste)",
}


def _source_category(
    result_category: str | None,
    table_key: str | None,
    extra_fields: dict[str, Any] | None,
) -> str:
    """Use stored reporting category, falling back to input classification only."""
    if result_category and result_category != "Stored carbon":
        return result_category

    extra = extra_fields or {}
    base_key = (table_key or "").split("-mitigation", 1)[0]
    if base_key == "shortcutSat4p":
        source = extra.get("source")
        return "Materials" if source == "Construction materials" else "Fuels"
    if base_key == "shortcutIsMaterials":
        return "Materials"

    category = extra.get("emissions_category")
    if category and category != "Offset":
        return str(category)

    if base_key in {"asset", "component", "concreteRegSimplified", "concreteRegDetailed"}:
        return "Materials"
    if base_key in {"electricity", "opEnergyElectricity", "opEnergy"}:
        return "Electricity"
    return "Other"


def aggregate_completeness_facts(
    facts: Iterable[dict[str, Any]],
    *,
    accounting_method: str = "location",
) -> dict[str, Any]:
    """Aggregate result facts without reading calculated amounts from inputs."""
    if accounting_method not in _ACCOUNTING_BASES:
        accounting_method = "location"
    allowed_bases = _ACCOUNTING_BASES[accounting_method]
    facts = list(facts)
    modules: defaultdict[str, Decimal] = defaultdict(Decimal)
    categories: defaultdict[str, Decimal] = defaultdict(Decimal)
    stored_carbon = Decimal(0)
    offsets = Decimal(0)
    annual_b8_options = {
        (
            fact.get("project_option_id") or fact.get("activity_option_id"),
            fact.get("source_category"),
        )
        for fact in facts
        if fact.get("lifecycle_module_code") == "B8"
        and fact.get("activity_data_id") is None
        and fact.get("source_category") in {"Road user transport", "Rail user transport"}
    }
    large_road_fallback: defaultdict[tuple, Decimal] = defaultdict(Decimal)

    for fact in facts:
        if fact["is_supplementary"] or fact["accounting_basis"] not in allowed_bases:
            continue

        measure = fact["reporting_measure"]
        value = Decimal(str(fact["value"] or 0))
        table_key = fact.get("ui_table_key")

        if measure == "stored_carbon":
            stored_carbon += value
            continue
        if measure == "offset":
            offsets -= abs(value)
            continue
        if measure not in {"actual", "mitigation"}:
            # Baseline adjustments and completeness uplifts are not base emissions.
            continue

        module_code = fact.get("lifecycle_module_code")
        if module_code == "B8":
            option_id = fact.get("activity_option_id") or fact.get("project_option_id")
            family = (
                "Rail user transport"
                if table_key in {"railUsers", "largeRailUsers"}
                else "Road user transport"
            )
            if fact.get("activity_data_id") is None:
                # Annual ledger results replace their linked legacy summary facts.
                modules["b8"] += value
                continue
            if (option_id, family) in annual_b8_options:
                continue
            # Compatibility with already-ledgered projects whose annual specialist
            # facts have not yet been synchronized. Keep the old report's inputs.
            if table_key not in {"roadUsers", "railUsers", "largeRoadParams"}:
                continue
            if table_key == "largeRoadParams":
                extra = fact.get("extra_fields") or {}
                group_key = (
                    option_id,
                    extra.get("gradient"),
                    extra.get("curvature"),
                    extra.get("roughness"),
                    extra.get("ev_uptake_scenario"),
                )
                large_road_fallback[group_key] = max(large_road_fallback[group_key], value)
                continue
            modules["b8"] += value
            continue

        include_module = True
        if table_key == "shortcutSat4p":
            source = (fact.get("extra_fields") or {}).get("source")
            # Preserve Completeness's established allocation: only these SAT4P
            # sources contribute to A5; materials/transport/maintenance sources
            # remain represented in source categories as before.
            if module_code != "A5" or source not in _A5_SAT4P_SOURCES:
                include_module = False

        field = _MODULE_FIELDS.get(module_code)
        if field and include_module:
            modules[field] += value

        # Prefer the category stored on a ledger fact. Table-key membership is
        # needed only when the category must be inferred from input metadata.
        if (fact.get("source_category") or table_key in _SOURCE_CATEGORY_TABLE_KEYS) and not (
            table_key == "shortcutIsMaterials"
            and (fact.get("extra_fields") or {}).get("row_type") == "maintenance"
        ):
            category = _source_category(
                fact.get("source_category"), table_key, fact.get("extra_fields")
            )
            categories[category] += value

    modules["b8"] += sum(large_road_fallback.values(), Decimal(0))
    modules["offsets"] = offsets
    modules["stored_carbon"] = stored_carbon
    for field in _MODULE_FIELDS.values():
        modules.setdefault(field, Decimal(0))
    modules.setdefault("b8", Decimal(0))
    return {
        "modules": dict(modules),
        "source_categories": {
            category: value
            for category, value in sorted(categories.items(), key=lambda item: item[1], reverse=True)
            if value > 0
        },
    }


async def get_completeness_emissions_totals(
    db: AsyncSession,
    *,
    project_id: UUID,
    stage_instance_id: UUID,
    project_option_id: UUID | None,
    submission_period_id: UUID | None,
    accounting_method: str,
) -> dict[str, Any]:
    """Fetch scoped result facts, including annual facts without an input row."""
    query = (
        select(
            EmissionsResult.value,
            EmissionsResult.lifecycle_module_code,
            EmissionsResult.source_category,
            EmissionsResult.accounting_basis,
            EmissionsResult.reporting_measure,
            EmissionsResult.is_supplementary,
            EmissionsResult.activity_data_id,
            EmissionsResult.project_option_id.label("result_option_id"),
            ActivityData.ui_table_key,
            ActivityData.extra_fields,
            ActivityData.project_option_id.label("activity_option_id"),
            ActivityData.submission_period_id,
        )
        .outerjoin(ActivityData, ActivityData.id == EmissionsResult.activity_data_id)
        .where(
            EmissionsResult.project_id == project_id,
            EmissionsResult.project_stage_instance_id == stage_instance_id,
            (ActivityData.id.is_(None)) | (ActivityData.ui_table_key != "completeness"),
        )
    )
    if project_option_id is not None:
        query = query.where(
            func.coalesce(EmissionsResult.project_option_id, ActivityData.project_option_id)
            == project_option_id
        )
    if submission_period_id is not None:
        # Annual facts have no period dimension, so they cannot be attributed to a
        # specific construction period and are excluded from period-scoped totals.
        query = query.where(ActivityData.submission_period_id == submission_period_id)

    rows = (await db.execute(query)).mappings().all()
    facts = [
        {
            "value": row["value"],
            "lifecycle_module_code": row["lifecycle_module_code"],
            "source_category": row["source_category"],
            "accounting_basis": row["accounting_basis"],
            "reporting_measure": row["reporting_measure"],
            "is_supplementary": row["is_supplementary"],
            "activity_data_id": row["activity_data_id"],
            "project_option_id": row["result_option_id"],
            "ui_table_key": row["ui_table_key"],
            "extra_fields": row["extra_fields"],
            "activity_option_id": row["activity_option_id"],
        }
        for row in rows
    ]
    return aggregate_completeness_facts(facts, accounting_method=accounting_method)
