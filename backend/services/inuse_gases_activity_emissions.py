from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.inuse_gases_component_level_calcs import InUseGasesCalculator, InUseGasesRequest
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)

_calculator = InUseGasesCalculator()


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_inuse_gases_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "useB1G2"):
        return None

    extra = dict(activity_row.extra_fields or {})
    application_type = _pick_label(extra.get("application_type")).strip()
    gas = _pick_label(extra.get("gas")).strip()
    gas_type_raw = extra.get("gas_type")
    gas_type: Optional[str] = _pick_label(gas_type_raw).strip() or None
    charge_kg_raw = extra.get("charge_kg")

    if not application_type or not gas or charge_kg_raw is None:
        logger.debug(
            "useB1G2 skip: missing required inputs activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        charge_kg = float(charge_kg_raw)
        if charge_kg <= 0:
            raise ValueError("charge_kg must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "useB1G2 skip: invalid charge_kg activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)
    except Exception as exc:
        logger.warning(
            "useB1G2 skip: could not resolve jurisdiction activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    ops_start: Optional[int] = None
    ops_end: Optional[int] = None
    try:
        project = await ProjectContextHelper.fetch_project(db, activity_row.project_id)
        ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
    except ValueError:
        pass

    if ops_start is None or ops_end is None:
        logger.warning(
            "useB1G2 skip: ops years unavailable activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        req = InUseGasesRequest(
            jurisdiction=jurisdiction,
            ops_start=ops_start,
            ops_end=ops_end,
            application_type=application_type,
            gas_type=gas_type,
            gas=gas,
            charge_kg=charge_kg,
        )
    except Exception as exc:
        logger.warning(
            "useB1G2 skip: invalid request activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    try:
        resp = await _calculator.calculate(db, req)
    except Exception:
        logger.exception(
            "useB1G2 calculate unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    if resp.total_emissions_tco2e is None:
        logger.warning(
            "useB1G2: calculator returned None "
            "(leakage_rate=%s scope1_factor=%s) activity_data=%s",
            resp.annual_leakage_rate_percent,
            resp.scope1_emissions_factor_tco2e_per_kg,
            activity_row.id,
        )
        return None

    scope1 = Decimal(str(resp.scope1_emissions_tco2e or 0))
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
        value=scope1,
    )
    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal("0"),
    )
    return total
