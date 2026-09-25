from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.grade2_b4_replacement_calculations import (
    Grade2B4ReplacementCalculator,
    Grade2B4ReplacementRequest,
)
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)

_calculator = Grade2B4ReplacementCalculator()


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_grade2_b4_replacement_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "componentRepl"):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_category = _pick_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_label(extra.get("emissions_subcategory")).strip()
    emissions_source = _pick_label(extra.get("emissions_source_name")).strip()
    life_raw = extra.get("life")

    if not emissions_category or not emissions_sub_category or not emissions_source:
        logger.debug(
            "grade2_b4_replacement skip: missing category/sub/source activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        life_years = float(life_raw)
        if life_years <= 0:
            raise ValueError("life_years must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "grade2_b4_replacement skip: invalid life=%r activity_data=%s",
            life_raw,
            activity_row.id,
        )
        return None

    try:
        qty = float(activity_row.quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "grade2_b4_replacement skip: invalid quantity activity_data=%s",
            activity_row.id,
        )
        return None

    req = Grade2B4ReplacementRequest(
        project_id=activity_row.project_id,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        quantity=qty,
        life_years=life_years,
    )

    try:
        resp = await _calculator.calculate(db, req)
    except ValueError as exc:
        logger.warning(
            "grade2_b4_replacement calculate failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None
    except Exception:
        logger.exception(
            "grade2_b4_replacement unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    tco2e = Decimal(str(resp.total_emissions_tco2e))
    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(
        **common,
        value_key="B2-5",
        lifecycle_module_code="B2-5",
        value=tco2e,
    )
    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=tco2e,
    )
    return tco2e
