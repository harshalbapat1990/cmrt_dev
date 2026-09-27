"""
Electricity Detailed Level emissions for activity_data rows.

Electricity source and mitigation substitution legs store inputs in extra_fields
and rely on ElectricityDetailedCalculator rather than BackgroundGradeMetric.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from crud.activity_data import update_activity_data
from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from schemas.activity_data import ActivityDataUpdate
from services.electricity_detailed_calculations import (
    ElectricityDetailedCalculator,
    ElectricityDetailedRequest,
)
from services.auto_substitution_mitigation import pick_emissions_source_label
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import mitigation_base_table_key

logger = logging.getLogger(__name__)

_BASE_ELECTRICITY_KEYS = frozenset({"electricity", "opEnergyElectricity"})

_calculator = ElectricityDetailedCalculator()


def electricity_base_table_key(ui_table_key: str) -> Optional[str]:
    base = mitigation_base_table_key(ui_table_key)
    if base in _BASE_ELECTRICITY_KEYS:
        return base
    return None


def is_electricity_activity_row(activity_row: ActivityData) -> bool:
    return electricity_base_table_key(activity_row.ui_table_key or "") is not None


async def recalc_electricity_activity_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    """Run electricity calculator from row fields; persist totals in extra_fields."""
    base_key = electricity_base_table_key(activity_row.ui_table_key or "")
    if base_key is None:
        return None

    extra = dict(activity_row.extra_fields or {})
    source = pick_emissions_source_label(extra.get("emission_source")).strip()
    if not source:
        return None

    year_raw = extra.get("year")
    if year_raw is None or year_raw == "":
        return None
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return None

    qty_raw = extra.get("quantity_mwh", activity_row.quantity)
    try:
        qty = float(qty_raw)
    except (TypeError, ValueError):
        return None
    if qty <= 0:
        return None

    unit = extra.get("unit_display") or "MWh"

    try:
        project = await ProjectContextHelper.fetch_project(db, activity_row.project_id)
    except ValueError:
        return None

    req_kwargs: dict[str, Any] = {
        "project_id": activity_row.project_id,
        "emission_source": source,
        "year": year,
        "quantity": qty,
        "unit": unit,
        "project_stage_instance_id": activity_row.project_stage_instance_id,
        "project_option_id": activity_row.project_option_id,
        "dataset_revision_id": activity_row.dataset_revision_id,
        # The request contract names the mitigation table generically while
        # activity rows may carry the adopted/replaced substitution suffix.
        "ui_table_key": (
            "electricity-mitigation"
            if "-mitigation" in (activity_row.ui_table_key or "")
            else base_key
        ),
    }

    if base_key == "electricity":
        if project.construction_start_date and project.construction_end_date:
            req_kwargs["construction_start_year"] = project.construction_start_date.year
            req_kwargs["construction_end_year"] = project.construction_end_date.year
    elif base_key == "opEnergyElectricity":
        try:
            ops_start, ops_end = ProjectContextHelper.get_operational_years(project)
            req_kwargs["ops_start_year"] = ops_start
            req_kwargs["ops_end_year"] = ops_end
        except ValueError:
            pass

    try:
        resp = await _calculator.calculate(db, ElectricityDetailedRequest(**req_kwargs))
    except ValueError as exc:
        logger.warning(
            "electricity calculate failed activity_data=%s key=%s: %s",
            activity_row.id,
            activity_row.ui_table_key,
            exc,
        )
        return None
    except Exception:
        logger.exception(
            "electricity calculate unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    lb = resp.location_based_total_tco2e
    mb = resp.market_based_total_tco2e
    total = lb if lb is not None else mb

    extra["location_based_tco2e"] = lb
    extra["market_based_tco2e"] = mb
    extra["total_emissions_tco2e"] = total
    extra["emissions_tco2e"] = total
    extra["unit_display"] = unit
    extra["quantity_mwh"] = extra.get("quantity_mwh") or activity_row.quantity

    await update_activity_data(
        db,
        activity_row.id,
        ActivityDataUpdate(extra_fields=extra),
    )

    if total is None:
        return None

    tco2e_dec = Decimal(str(total))
    lc = activity_row.lifecycle_module_code or "A5"
    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(
        **common,
        value_key=lc,
        lifecycle_module_code=lc,
        value=tco2e_dec,
        accounting_basis="location",
    )
    if mb is not None:
        await upsert_result(
            **common,
            value_key=f"{lc}_market",
            lifecycle_module_code=lc,
            value=Decimal(str(mb)),
            accounting_basis="market",
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
    return tco2e_dec
