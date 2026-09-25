from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.detailed_level_calcs_operational_fuel_water import (
    DetailedLevelFuelWaterCalculator,
    DetailedLevelFuelWaterRequest,
)
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)

_calculator = DetailedLevelFuelWaterCalculator()


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_operational_fuel_water_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "opEnergyDetailed"):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_category = _pick_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_label(extra.get("emissions_subcategory")).strip()
    emissions_source = _pick_label(extra.get("emissions_source_name")).strip()
    unit = _pick_label(extra.get("unit_code")).strip()
    period_raw = _pick_label(extra.get("period")).strip().lower()
    period_map = {
        "annual": "Annual Average",
        "annual average": "Annual Average",
        "average annual life": "Annual Average",
        "total": "Total Operational Life",
        "total operational life": "Total Operational Life",
    }
    period = period_map.get(period_raw, "Total Operational Life")

    if not emissions_category or not emissions_sub_category or not emissions_source:
        logger.debug(
            "opEnergyDetailed skip: missing category/sub/source activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        qty = float(activity_row.quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "opEnergyDetailed skip: invalid quantity activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)
    except ValueError as exc:
        logger.warning(
            "opEnergyDetailed skip: project context unavailable activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    req = DetailedLevelFuelWaterRequest(
        jurisdiction=jurisdiction,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        unit=unit or None,
        quantity=qty,
        period=period,
        project_id=activity_row.project_id,
    )

    try:
        resp = await _calculator.calculate(db, req)
    except Exception:
        logger.exception(
            "opEnergyDetailed unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    tco2e = Decimal(str(resp.total_emissions_tco2e))
    lifecycle_module = "B7" if emissions_category == "Water" else "B6"

    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(
        **common,
        value_key=lifecycle_module,
        lifecycle_module_code=lifecycle_module,
        value=tco2e,
    )
    await upsert_result(
        **common,
        value_key="scope1",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope1_emissions_tco2e or 0)),
    )
    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope3_emissions_tco2e or 0)),
    )
    return tco2e
