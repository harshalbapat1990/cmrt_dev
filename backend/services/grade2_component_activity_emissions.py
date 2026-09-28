from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.grade2_component_calculations import Grade2CalculationRequest, calculator
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import mitigation_base_table_key

logger = logging.getLogger(__name__)

SUPPORTED_GRADE2_TABLES = {
    "component",
    "constructionG2",
}

def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_grade2_component_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    key = mitigation_base_table_key(activity_row.ui_table_key)
    if key not in SUPPORTED_GRADE2_TABLES:
        return None

    extra = dict(activity_row.extra_fields or {})

    emissions_category     = _pick_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_label(extra.get("emissions_subcategory")).strip()
    emissions_source       = _pick_label(extra.get("emissions_source_name")).strip()

    if not emissions_category or not emissions_sub_category or not emissions_source:
        logger.debug(
            "grade2_component skip: missing category/sub-category/source activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        quantity = float(activity_row.quantity)
        if quantity <= 0:
            raise ValueError("quantity must be positive")
    except (TypeError, ValueError) as exc:
        logger.debug(
            "grade2_component skip: invalid quantity activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)

    req = Grade2CalculationRequest(
        jurisdiction=jurisdiction,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        quantity=quantity,
    )

    try:
        resp = await calculator.calculate(db, req)
    except ValueError as exc:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            from services.project_dataset_recalculation import MissingDatasetDataError

            raise MissingDatasetDataError("Grade 2 component factors", str(exc)) from exc
        logger.warning(
            "grade2_component skip: lookup failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    a1a3  = Decimal(str(resp.product_stage_a1_a3_tco2e))
    a4    = Decimal(str(resp.transport_stage_a4_tco2e))
    a5    = Decimal(str(resp.construction_stage_a5_tco2e))
    total = Decimal(str(resp.total_emissions_tco2e))

    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )

    await upsert_result(**common, value_key="A1-A3", lifecycle_module_code="A1-A3", value=a1a3)
    await upsert_result(**common, value_key="A4",    lifecycle_module_code="A4",    value=a4)
    await upsert_result(**common, value_key="A5",    lifecycle_module_code="A5",    value=a5)
    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=total,
    )

    return total
