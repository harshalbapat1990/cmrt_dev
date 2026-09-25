from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from models.units import Unit
from services.grade34_detailed_level_maintenance_calcs import (
    Grade34MaintenanceRequest,
    calculator as grade34_maintenance_calculator,
)
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_shortcut_is_materials_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "shortcutIsMaterials"):
        return None

    extra = dict(activity_row.extra_fields or {})
    if extra.get("row_type") == "maintenance":
        return None

    actual_case_raw = extra.get("actual_case")
    if actual_case_raw is None or actual_case_raw == "":
        return None

    try:
        total = Decimal(str(float(actual_case_raw)))
    except (TypeError, ValueError):
        logger.debug(
            "shortcutIsMaterials skip: invalid actual_case activity_data=%s",
            activity_row.id,
        )
        return None

    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(**common, value_key="A1-A3", lifecycle_module_code="A1-A3", value=total)
    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=total,
    )
    return total


async def recalc_use_b1g3_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "useB1G3"):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_category = _pick_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_label(extra.get("emissions_subcategory")).strip()
    emissions_source = _pick_label(extra.get("emissions_source_name")).strip()
    unit = _pick_label(extra.get("unit_code")).strip()

    _period_map: dict[str, str] = {
        "annual": "Annual",
        "annual average": "Annual",
        "total": "Total Operational Life",
        "total operational life": "Total Operational Life",
    }
    period = _period_map.get(_pick_label(extra.get("period")).strip().lower(), "")

    try:
        qty_f = float(activity_row.quantity)
        if qty_f <= 0 or qty_f != qty_f:
            raise ValueError
    except (TypeError, ValueError):
        return None

    if not emissions_category or not emissions_sub_category or not emissions_source or not unit or not period:
        return None

    canonical_unit_id_raw = extra.get("canonical_unit_id")
    unit_conversion_factor_raw = extra.get("unit_conversion_factor")
    if canonical_unit_id_raw and unit_conversion_factor_raw:
        try:
            import uuid as _uuid_mod
            canon_uid = _uuid_mod.UUID(str(canonical_unit_id_raw))
            conv_factor = float(unit_conversion_factor_raw)
            canon_unit_result = await db.execute(select(Unit).where(Unit.id == canon_uid))
            canon_unit = canon_unit_result.scalars().first()
            if canon_unit:
                unit = canon_unit.code
                qty_f = qty_f * conv_factor
        except Exception as _conv_err:
            logger.warning(
                "useB1G3 unit conversion failed activity_data=%s: %s",
                activity_row.id,
                _conv_err,
            )

    try:
        project = await ProjectContextHelper.fetch_project(db, activity_row.project_id)
        ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
    except ValueError as exc:
        logger.warning(
            "useB1G3 project context failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)
    req = Grade34MaintenanceRequest(
        jurisdiction=jurisdiction,
        ops_start=ops_start,
        ops_end=ops_end,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        period=period,
        unit=unit,
        quantity=qty_f,
    )

    try:
        resp = await grade34_maintenance_calculator.calculate(db, req)
    except ValueError as exc:
        logger.warning(
            "useB1G3 calculate failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None
    except Exception:
        logger.exception(
            "useB1G3 calculate unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    total = Decimal(str(resp.total_emissions_tco2e))
    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(**common, value_key="B1", lifecycle_module_code="B1", value=total)
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
    return total
