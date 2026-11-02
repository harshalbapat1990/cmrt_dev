from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from services.ui_table_key_normalization import mitigation_base_table_key

logger = logging.getLogger(__name__)

_CONCRETE_TABLE_KEYS = frozenset({"concreteRegSimplified", "concreteRegDetailed"})


async def recalc_concrete_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    key = mitigation_base_table_key(activity_row.ui_table_key)
    if key not in _CONCRETE_TABLE_KEYS:
        return None

    extra = dict(activity_row.extra_fields or {})
    gwp_a1a3_raw = extra.get("gwp_a1a3_tco2e_m3")
    transport_a4_raw = extra.get("transport_a4_ef_tco2e_m3")
    total_raw = extra.get("total_emissions_tco2e")

    try:
        qty = float(activity_row.quantity)
        if qty <= 0 or qty != qty:
            raise ValueError("quantity must be > 0")
    except (TypeError, ValueError):
        logger.debug(
            "concrete skip: invalid quantity activity_data=%s",
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

    if gwp_a1a3_raw is not None and transport_a4_raw is not None:
        try:
            a1a3 = Decimal(str(float(gwp_a1a3_raw))) * Decimal(str(qty))
            a4 = Decimal(str(float(transport_a4_raw))) * Decimal(str(qty))
        except (TypeError, ValueError) as exc:
            logger.debug(
                "concrete skip: invalid factor values activity_data=%s: %s",
                activity_row.id,
                exc,
            )
            return None
        total = a1a3 + a4
        await upsert_result(**common, value_key="A1-A3", lifecycle_module_code="A1-A3", value=a1a3)
        await upsert_result(**common, value_key="A4", lifecycle_module_code="A4", value=a4)
    elif total_raw is not None:
        try:
            total = Decimal(str(float(total_raw)))
        except (TypeError, ValueError) as exc:
            logger.debug(
                "concrete skip: invalid total_emissions_tco2e activity_data=%s: %s",
                activity_row.id,
                exc,
            )
            return None
        await upsert_result(**common, value_key="A1-A3", lifecycle_module_code="A1-A3", value=total)
    else:
        logger.debug(
            "concrete skip: no factors or total in extra_fields activity_data=%s",
            activity_row.id,
        )
        return None

    await upsert_result(
        **common,
        value_key="scope3",
        lifecycle_module_code=None,
        is_supplementary=True,
        value=total,
    )
    return total
