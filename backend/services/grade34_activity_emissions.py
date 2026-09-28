"""
Grade 3/4 Detailed Level (construction stage) emissions for activity_data rows.

The activity_data ORM does not expose metric_id; Detailed Level relies on grade34-construction-
calculator inputs in extra_fields. calculate_and_store() cannot resolve a BackgroundGradeMetric,
so these rows must use the Grade34ConstructionCalculator instead.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from models.units import Unit
from services.grade34_detailed_level_construction_calcs import (
    Grade34ConstructionRequest,
    calculator as grade34_construction_calculator,
)
from services.project_context_helper import ProjectContextHelper
from services.ui_table_key_normalization import mitigation_base_table_key

logger = logging.getLogger(__name__)

_BASE_GRADE34_CONSTRUCTION_KEYS = frozenset({"bcDetailedLevel", "constructionG3", "recurringG3"})


def _pick_extra_label(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


def is_grade34_detailed_construction_activity_row(activity_row: ActivityData) -> bool:
    """True for Detailed Level / construction substitution legs that use Grade34ConstructionCalculator."""
    base = mitigation_base_table_key(activity_row.ui_table_key)
    return base in _BASE_GRADE34_CONSTRUCTION_KEYS


async def recalc_grade34_construction_activity_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    """
    Run Grade 3/4 construction calculator from row.quantity + extra_fields, persist totals
    in extra_fields and a single emissions_results row (for API enrich_with_emissions).
    Returns total tCO2e or None if inputs are insufficient / calculation fails.
    """
    if not is_grade34_detailed_construction_activity_row(activity_row):
        return None

    extra = dict(activity_row.extra_fields or {})
    emissions_category = _pick_extra_label(extra.get("emissions_category")).strip()
    emissions_sub_category = _pick_extra_label(extra.get("emissions_subcategory")).strip()
    emissions_source = _pick_extra_label(extra.get("emissions_source_name")).strip()
    unit = _pick_extra_label(extra.get("unit_code")).strip()

    try:
        qty_f = float(activity_row.quantity)
    except (TypeError, ValueError):
        qty_f = float("nan")

    canonical_unit_id_raw = extra.get("canonical_unit_id")
    unit_conversion_factor_raw = extra.get("unit_conversion_factor")

    if canonical_unit_id_raw and unit_conversion_factor_raw:
        try:
            import uuid as _uuid_mod
            canon_uid = _uuid_mod.UUID(str(canonical_unit_id_raw))
            conv_factor = float(unit_conversion_factor_raw)
            canon_unit_result = await db.execute(
                select(Unit).where(Unit.id == canon_uid)
            )
            canon_unit = canon_unit_result.scalars().first()
            if canon_unit:
                unit = canon_unit.code
                qty_f = qty_f * conv_factor
        except Exception as _conv_err:
            logger.warning(
                "grade34 unit conversion failed activity_data=%s: %s",
                activity_row.id,
                _conv_err,
            )

    if (
        not emissions_category
        or not emissions_sub_category
        or not emissions_source
        or not unit
        or qty_f <= 0
        or qty_f != qty_f  # NaN
    ):
        logger.debug(
            "grade34 activity skip: insufficient inputs activity_data=%s key=%s",
            activity_row.id,
            activity_row.ui_table_key,
        )
        return None

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, activity_row.project_id)
    req = Grade34ConstructionRequest(
        jurisdiction=jurisdiction,
        emissions_category=emissions_category,
        emissions_sub_category=emissions_sub_category,
        emissions_source=emissions_source,
        unit=unit,
        quantity=qty_f,
    )

    try:
        resp = await grade34_construction_calculator.calculate(db, req)
    except ValueError as exc:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            from services.project_dataset_recalculation import MissingDatasetDataError

            raise MissingDatasetDataError("Grade 3/4 detailed level factors", str(exc)) from exc
        logger.warning(
            "grade34 calculate failed activity_data=%s key=%s: %s",
            activity_row.id,
            activity_row.ui_table_key,
            exc,
        )
        return None
    except Exception:
        if getattr(activity_row, "_strict_dataset_recalculation", False):
            raise
        logger.exception(
            "grade34 calculate unexpected error activity_data=%s",
            activity_row.id,
        )
        return None

    total_float = float(resp.total_emissions_tco2e)

    # Keep source lookup gaps on the in-memory row for the revision-switch
    # report without exposing internal calculation metadata to data-entry APIs.
    activity_row._dataset_data_warnings = list(resp.data_warnings)

    common = dict(
        db=db,
        project_id=activity_row.project_id,
        project_stage_instance_id=activity_row.project_stage_instance_id,
        activity_data_id=activity_row.id,
        unit_id=activity_row.unit_id,
    )
    await upsert_result(
        **common,
        value_key="A1-A3",
        lifecycle_module_code="A1-A3",
        value=Decimal(str(resp.product_stage_a1_a3_tco2e)),
    )
    await upsert_result(
        **common,
        value_key="A4",
        lifecycle_module_code="A4",
        value=Decimal(str(resp.transport_stage_a4_tco2e)),
    )
    await upsert_result(
        **common,
        value_key="A5",
        lifecycle_module_code="A5",
        value=Decimal(str(resp.construction_stage_a5_tco2e)),
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

    tco2e_dec = Decimal(str(resp.total_emissions_tco2e))
    return tco2e_dec
