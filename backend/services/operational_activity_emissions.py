from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.operational_component_level_calcs import (
    OperationalComponentCalculator,
    OperationalComponentRequest,
    VALID_EMISSION_SOURCE_TYPES,
)
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import matches_base_table_key

logger = logging.getLogger(__name__)

_calculator = OperationalComponentCalculator()


def _pick_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


async def recalc_operational_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    if not matches_base_table_key(activity_row.ui_table_key, "opEnergy"):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_source = _pick_label(extra.get("emissions_source")).strip()
    if not emissions_source:
        logger.debug(
            "opEnergy skip: missing emissions_source activity_data=%s",
            activity_row.id,
        )
        return None

    emission_source_type = _pick_label(extra.get("emission_source_type")).strip()
    if emission_source_type not in VALID_EMISSION_SOURCE_TYPES:
        emission_source_type = "Grid Electricity"

    try:
        qty = float(activity_row.quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "opEnergy skip: invalid quantity activity_data=%s",
            activity_row.id,
        )
        return None

    try:
        ctx = await ProjectContextHelper.get_project_context(db, activity_row.project_id)
    except ValueError as exc:
        logger.warning(
            "opEnergy skip: project context unavailable activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    try:
        req = OperationalComponentRequest(
            project_id=activity_row.project_id,
            jurisdiction=ctx["jurisdiction"],
            ops_start=ctx["operations_start_year"],
            ops_end=ctx["operations_end_year"],
            emissions_source=emissions_source,
            quantity=qty,
            emission_source_type=emission_source_type,
        )
    except Exception as exc:
        logger.warning(
            "opEnergy skip: invalid request activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None

    try:
        resp = await _calculator.calculate(db, req)
    except ValueError as exc:
        logger.warning(
            "opEnergy calculate failed activity_data=%s: %s",
            activity_row.id,
            exc,
        )
        return None
    except Exception:
        logger.exception(
            "opEnergy unexpected error activity_data=%s",
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
    await upsert_result(
        **common,
        value_key="B6",
        lifecycle_module_code="B6",
        is_supplementary=False,
        value=Decimal(str(resp.location_based_total_tco2e or 0)),
        accounting_basis="location",
    )
    await upsert_result(
        **common,
        value_key="scope2_location",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope2_location_based_tco2e or 0)),
    )
    await upsert_result(
        **common,
        value_key="scope2_market",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope2_market_based_tco2e or 0)),
    )
    await upsert_result(
        **common,
        value_key="scope3_location",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope3_location_based_tco2e or 0)),
    )
    await upsert_result(
        **common,
        value_key="scope3_market",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=Decimal(str(resp.scope3_market_based_tco2e or 0)),
    )

    lb = resp.location_based_total_tco2e
    return Decimal(str(lb)) if lb is not None else Decimal(0)
