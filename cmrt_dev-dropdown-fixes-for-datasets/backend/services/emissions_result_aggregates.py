"""Shared dashboard aggregation over the emissions result ledger."""
from collections import defaultdict
from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_data import ActivityData
from models.emissions_results import EmissionsResult


async def emissions_totals_by_activity(
    db: AsyncSession,
    activity_data_ids: Iterable[UUID],
    *,
    accounting_method: str = "location",
    measures: tuple[str, ...] = ("actual", "mitigation"),
) -> dict[UUID, Decimal]:
    """Return per-input emissions totals from the canonical ledger.

    Input rows may still supply labels and quantities, but reportable amounts
    are selected here so detailed and summary dashboard paths share the same
    treatment of accounting basis and reporting measure.
    """
    ids = list(set(activity_data_ids))
    if not ids:
        return {}
    bases = ("common", "location") if accounting_method == "location" else ("common", "market")
    query = (
        select(EmissionsResult.activity_data_id, EmissionsResult.value)
        .where(
            EmissionsResult.activity_data_id.in_(ids),
            EmissionsResult.is_supplementary.is_(False),
            EmissionsResult.reporting_measure.in_(measures),
            EmissionsResult.accounting_basis.in_(bases),
        )
    )
    totals: dict[UUID, Decimal] = {}
    for activity_id, value in (await db.execute(query)).all():
        totals[activity_id] = totals.get(activity_id, Decimal(0)) + Decimal(str(value or 0))
    return totals


async def aggregate_emissions_results(
    db: AsyncSession,
    *,
    project_id: UUID,
    stage_instance_id: UUID,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
    accounting_method: str = "location",
) -> dict:
    """Return consistent module, category, scope and mitigation totals.

    Input rows are joined only to apply report context and retain dimensions that
    describe the source input. All numeric emissions values come from results.
    """
    query = (
        select(EmissionsResult, ActivityData.ui_table_key, ActivityData.extra_fields)
        .join(ActivityData, ActivityData.id == EmissionsResult.activity_data_id)
        .where(
            EmissionsResult.project_id == project_id,
            EmissionsResult.project_stage_instance_id == stage_instance_id,
            ActivityData.project_id == project_id,
            ActivityData.project_stage_instance_id == stage_instance_id,
        )
    )
    if project_option_id is not None:
        query = query.where(ActivityData.project_option_id == project_option_id)
    if submission_period_id is not None:
        query = query.where(ActivityData.submission_period_id == submission_period_id)
    rows = (await db.execute(query)).all()
    modules = defaultdict(Decimal)
    categories = defaultdict(Decimal)
    scopes = defaultdict(Decimal)
    scope_breakdown = defaultdict(Decimal)
    mitigation = defaultdict(Decimal)
    baseline_adjustment = defaultdict(Decimal)
    mitigation_modules = defaultdict(Decimal)
    stored_carbon = Decimal(0)
    large_road_values = defaultdict(Decimal)

    for result, ui_table_key, extra_fields in rows:
        basis = result.accounting_basis or "common"
        if basis == "market" and accounting_method != "market":
            continue
        if basis == "location" and accounting_method == "market":
            continue
        value = Decimal(str(result.value or 0))
        measure = result.reporting_measure or "actual"
        if measure == "stored_carbon":
            stored_carbon += value
            continue
        if measure == "baseline_adjustment":
            baseline_adjustment[result.lifecycle_module_code or "other"] += value
            continue
        if result.is_supplementary:
            if result.emissions_scope:
                scopes[result.emissions_scope] += value
                base_key = ui_table_key.split("-mitigation", 1)[0]
                phase = "construction" if base_key in {
                    "asset", "component", "bcDetailedLevel", "constructionG2",
                    "constructionG3", "electricity", "concreteRegSimplified",
                    "concreteRegDetailed", "shortcutSat4p",
                } else "operations"
                if measure == "actual":
                    scope_breakdown[(result.emissions_scope, phase, "actual")] += value
                    scope_breakdown[(result.emissions_scope, phase, "baseline")] += value
                elif measure == "mitigation":
                    scope_breakdown[(result.emissions_scope, phase, "baseline")] += value
            continue
        if measure == "offset":
            modules["Offsets"] -= abs(value)
            continue
        if basis not in {"common", "location", "market"}:
            continue
        if measure == "mitigation":
            mitigation[ui_table_key] += value
            if result.lifecycle_module_code:
                mitigation_modules[result.lifecycle_module_code] += value
            continue
        module = result.lifecycle_module_code
        if module:
            if ui_table_key == "largeRoadParams" and module == "B8":
                extra = extra_fields or {}
                group = tuple(str(extra.get(k) or "") for k in (
                    "gradient", "curvature", "roughness", "ev_uptake_scenario",
                ))
                large_road_values[group] = max(large_road_values[group], value)
            else:
                modules[module] += value
        category = result.source_category
        if category:
            categories[category] += value

    # Large road parameters contain repeated yearly inputs for one parameter
    # group; the established report uses the maximum calculated total per group.
    modules["B8"] += sum(large_road_values.values(), Decimal(0))

    # The zero result from the non-selected electricity basis must not suppress
    # the selected method. Callers use the method-specific values above.
    return {
        "modules": dict(modules),
        "categories": dict(categories),
        "scopes": dict(scopes),
        "scope_breakdown": dict(scope_breakdown),
        "mitigation": dict(mitigation),
        "mitigation_modules": dict(mitigation_modules),
        "baseline_adjustment": dict(baseline_adjustment),
        "stored_carbon": stored_carbon,
    }
