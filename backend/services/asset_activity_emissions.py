from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.grade1_asset_calculations import Grade1CalculationRequest, calculator
from services.project_context_helper import ProjectContextHelper

logger = logging.getLogger(__name__)


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_asset_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    key = (activity_row.ui_table_key or "").split("-mitigation-subst-")[0]
    if key != "asset":
        return None

    extra = dict(activity_row.extra_fields or {})

    mastertype = _pick_label(extra.get("mastertype_name")).strip()
    typecast = _pick_label(extra.get("typecast_name")).strip()
    sensitivity = _pick_label(extra.get("band_code")).strip()
    functional_unit = (
        _pick_label(extra.get("canonical_unit_code") or extra.get("unit_code")).strip()
        or "CAPEX"
    )

    if not mastertype or not typecast or not sensitivity:
        logger.debug(
            "asset skip: missing mastertype/typecast/sensitivity activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        conv_factor = float(extra.get("unit_conversion_factor") or 1)
        quantity = float(activity_row.quantity) * conv_factor
        if quantity <= 0:
            raise ValueError("quantity must be positive")
    except (TypeError, ValueError) as exc:
        logger.debug(
            "asset skip: invalid quantity activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)

    req = Grade1CalculationRequest(
        jurisdiction=jurisdiction,
        mastertype=mastertype,
        typecast=typecast,
        sensitivity=sensitivity,
        quantity=quantity,
        functional_unit=functional_unit,
    )

    try:
        resp = await calculator.calculate(db, req)
    except ValueError as exc:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            from services.project_dataset_recalculation import MissingDatasetDataError

            raise MissingDatasetDataError("Grade 1 asset factors", str(exc)) from exc
        logger.warning(
            "asset skip: Grade1AssetCalculator lookup failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    a1a3  = Decimal(str(resp.product_stage_a1a3))
    a4    = Decimal(str(resp.transport_a4))
    a5    = Decimal(str(resp.construction_a5))
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
