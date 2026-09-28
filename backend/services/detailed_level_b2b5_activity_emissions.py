from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.detailed_level_maintenance_b2_b5_calcs import (
    DetailedMaintenanceB2B5Calculator,
    DetailedMaintenanceB2B5Request,
)
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)

_calculator = DetailedMaintenanceB2B5Calculator()


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_detailed_b2b5_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "replDetailed"):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_category = _pick_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_label(extra.get("emissions_subcategory")).strip()
    emissions_source = _pick_label(extra.get("emissions_source_name")).strip()
    unit = _pick_label(extra.get("unit_code")).strip()
    period = _pick_label(extra.get("period")).strip()

    if not emissions_category or not emissions_sub_category or not emissions_source or not unit or not period:
        logger.debug(
            "replDetailed skip: missing inputs activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        qty = float(activity_row.quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "replDetailed skip: invalid quantity activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        project = await ProjectContextHelper.fetch_project(db, activity_row.project_id)
        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)
        ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
    except ValueError as exc:
        logger.warning(
            "replDetailed skip: project context unavailable activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    req = DetailedMaintenanceB2B5Request(
        jurisdiction=jurisdiction,
        ops_start=ops_start,
        ops_end=ops_end,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        period=period,
        unit=unit,
        quantity=qty,
    )

    try:
        resp = await _calculator.calculate(db, req)
    except ValueError as exc:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            from services.project_dataset_recalculation import MissingDatasetDataError

            raise MissingDatasetDataError("Detailed level maintenance factors", str(exc)) from exc
        logger.warning(
            "replDetailed calculation lookup failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None
    except Exception:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            raise
        logger.exception(
            "replDetailed unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    if resp.total_emissions_tco2e is None:
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
