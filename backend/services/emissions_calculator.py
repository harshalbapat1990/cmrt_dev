# """
# Emissions Calculator
# ====================
# Resolves the emission factor from background_grade_metrics and stores a result
# row in emissions_results for the given activity_data record.

# Called synchronously from the activity_data router after every POST / PATCH so
# that the calculated tCO₂e is always up to date.

# Logic
# -----
# 1. Fetch the BackgroundGradeMetric via activity_data.metric_id.
# 2. If the metric has a `value` (the emission factor):
#        tCO₂e  =  quantity  ×  metric.value
# 3. Upsert a single emissions_results row using the metric's lifecycle_module_code
#    (falls back to None if the metric has no module code — still stored).
# 4. Return the total tCO₂e (Decimal).

# Future: If multiple lifecycle modules are needed (e.g. A1-A3 + A4), this service
# can be extended to emit multiple rows per activity_data record without any schema
# changes.
# """
from decimal import Decimal
from typing import Optional
from uuid import UUID

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from models.activity_data import ActivityData
from models.maintenance_replacement_factors import MaintenanceReplacementFactor
from models.jurisdictions import Jurisdiction
from models.project import Project
from crud.emissions_results import upsert_result
from crud.background_grade_metrics import (
    get_background_grade_metric_by_natural_key,
    get_background_grade_metric_orm,
)
from crud.unit_conversions import get_conversion_factor
from services.grade34_activity_emissions import (
    is_grade34_detailed_construction_activity_row,
    recalc_grade34_construction_activity_row,
)
from services.electricity_activity_emissions import recalc_electricity_activity_row
from services.grade2_b4_replacement_activity_emissions import recalc_grade2_b4_replacement_row
from services.detailed_level_b2b5_activity_emissions import recalc_detailed_b2b5_row
from services.operational_activity_emissions import recalc_operational_row
from services.operational_fuel_water_activity_emissions import recalc_operational_fuel_water_row
from services.asset_activity_emissions import recalc_asset_row
from services.grade2_component_activity_emissions import recalc_grade2_component_row
from services.concrete_activity_emissions import recalc_concrete_row
from services.shortcut_activity_emissions import recalc_shortcut_is_materials_row, recalc_use_b1g3_row
from services.inuse_gases_activity_emissions import recalc_inuse_gases_row
from services.calculation_errors import DatasetLookupError
from services.ui_table_key_normalization import mitigation_base_table_key
from services.ui_table_key_normalization import matches_base_table_key
from services.maintenance_replacement_component_level_calcs import (
    MaintenanceCalcRequest,
    calculator as maintenance_calculator,
)

logger = logging.getLogger(__name__)

_SPECIALIZED_CALCULATORS: dict[
    str, Callable[[AsyncSession, ActivityData], Awaitable[Optional[Decimal]]]
] = {
    "component": recalc_grade2_component_row,
    "constructionG2": recalc_grade2_component_row,
    "componentRepl": recalc_grade2_b4_replacement_row,
    "replDetailed": recalc_detailed_b2b5_row,
    "opEnergy": recalc_operational_row,
    "opEnergyDetailed": recalc_operational_fuel_water_row,
    "shortcutIsMaterials": recalc_shortcut_is_materials_row,
    "useB1G2": recalc_inuse_gases_row,
    "useB1G3": recalc_use_b1g3_row,
    "concreteRegSimplified": recalc_concrete_row,
    "concreteRegDetailed": recalc_concrete_row,
    "electricity": recalc_electricity_activity_row,
    "opEnergyElectricity": recalc_electricity_activity_row,
}

# These rows are calculated by the road-user year workflow (or contain only
# road-user parameters). Their reportable values are synchronized from their
# dedicated activity/annual-result records by result_ledger, so they must not
# be interpreted as generic quantity × background-factor rows.
_INDEPENDENT_CALCULATION_TABLES = frozenset({
    "roadUsers",
    "largeRoadUsers",
    "largeRoadParams",
})


def _has_dedicated_calculator(activity_row: ActivityData) -> bool:
    base_key = mitigation_base_table_key(activity_row.ui_table_key)
    return (
        is_grade34_detailed_construction_activity_row(activity_row)
        or base_key in {"asset", "railUsers", "largeRailUsers", "refurbishment"}
        or base_key in _SPECIALIZED_CALCULATORS
    )


async def _recalc_refurbishment_row(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    extra = activity_row.extra_fields or {}
    mr_factor_id = extra.get("mr_factor_id")
    if not mr_factor_id:
        return None

    factor_q = await db.execute(
        select(MaintenanceReplacementFactor).where(
            MaintenanceReplacementFactor.id == mr_factor_id
        )
    )
    factor = factor_q.scalars().first()
    if factor is None:
        return None

    jur_q = await db.execute(
        select(Jurisdiction).where(Jurisdiction.id == factor.jurisdiction_id)
    ) if factor.jurisdiction_id else None
    jur = jur_q.scalars().first() if jur_q else None
    jurisdiction_name = jur.name if jur else "Australia"

    project_q = await db.execute(
        select(Project).where(Project.id == activity_row.project_id)
    )
    project = project_q.scalars().first()
    reference_period = (
        float(project.operational_life_years)
        if project and project.operational_life_years
        else None
    )
    frequency_years = float(extra.get("frequency", 0) or 0)
    if not reference_period or frequency_years <= 0:
        return None

    calc_quantity = float(activity_row.quantity)
    if (
        activity_row.unit_id is not None
        and factor.unit_id is not None
        and activity_row.unit_id != factor.unit_id
    ):
        conv = await get_conversion_factor(
            db,
            activity_row.unit_id,
            factor.unit_id,
            activity_row.dataset_revision_id,
        )
        if conv is not None:
            calc_quantity *= float(conv)
        elif getattr(activity_row, "_strict_dataset_recalculation", False):
            from services.project_dataset_recalculation import MissingDatasetDataError

            raise MissingDatasetDataError(
                "Unit conversions",
                "No conversion exists between the entered unit and the selected maintenance factor unit.",
            )
        else:
            logger.warning(
                "calculate_and_store: no unit conversion from %s to factor unit %s "
                "for refurbishment activity_data %s; using raw quantity",
                activity_row.unit_id,
                factor.unit_id,
                activity_row.id,
            )

    req = MaintenanceCalcRequest(
        jurisdiction=jurisdiction_name,
        activity_type=factor.activity_type,
        item=factor.item,
        unit=factor.unit.code if factor.unit else "",
        quantity=calc_quantity,
        reference_period=reference_period,
        frequency_years=frequency_years,
    )
    calc_result = await maintenance_calculator.calculate(db, req)
    activity_row._dataset_data_warnings = list(calc_result.data_warnings or [])
    tco2e = Decimal(str(calc_result.total_emissions_tco2e))
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


async def _calculate_and_store_impl(
    db: AsyncSession,
    activity_row: ActivityData,
    *,
    raise_errors: bool = False,
) -> Optional[Decimal]:
    """
    Compute emissions for a single activity_data row and persist the result.

    Returns the calculated tCO₂e value (or None if the metric has no factor value).
    Raises no exceptions — errors are logged and None is returned so the caller
    can still return a successful HTTP response.
    """
    try:
        if activity_row.ui_table_key == "completeness":
            return None

        # Grade 3/4 rows use a source/category/sub-category/unit lookup in the
        # detailed-level calculator. Their legacy metric natural keys were
        # resolved using only category/sub-category and may point at a different
        # material (and unit), so never let those keys select the factor here.
        if is_grade34_detailed_construction_activity_row(activity_row):
            activity_row.metric_natural_key = None
            grade34_total = await recalc_grade34_construction_activity_row(db, activity_row)
            return grade34_total

        # Grade 1 assets have a multi-stage CAPEX calculation (material share
        # plus A1-A3/A4/A5 intensities). A resolved background metric is only a
        # legacy identity for these rows; applying its value directly to the
        # full quantity bypasses the Grade 1 formula and produces an inflated
        # ledger result. Always route asset rows through their dedicated
        # calculator before considering the generic metric path.
        if matches_base_table_key(activity_row.ui_table_key, "asset"):
            return await recalc_asset_row(db, activity_row)

        if mitigation_base_table_key(activity_row.ui_table_key) in {"railUsers", "largeRailUsers"}:
            extra = dict(activity_row.extra_fields or {})
            rail_type = str(extra.get("vehicle_type") or "").strip()
            terrain = str(extra.get("terrain") or "").strip()
            freight_raw = extra.get("freight") or getattr(activity_row, "quantity", None)
            if not rail_type or not terrain or freight_raw in (None, ""):
                return None
            from schemas.user_emissions_rail import RailEmissionsCalculateRequest
            from services.user_emissions_rail_calculations import calculate_rail

            try:
                rail_result = await calculate_rail(
                    db,
                    RailEmissionsCalculateRequest(
                        project_id=activity_row.project_id,
                        rail_type=rail_type,
                        terrain=terrain,
                        freight_quantity_gtk_per_year=Decimal(str(freight_raw)),
                    ),
                )
            except DatasetLookupError as exc:
                from services.project_dataset_recalculation import MissingDatasetDataError

                raise MissingDatasetDataError("Rail user-emissions factors", str(exc)) from exc
            extra.update({
                "emissions_intensity_tco2e_kl": str(rail_result.emissions_intensity_tco2e_kl),
                "emissions_annual_tco2e": str(rail_result.emissions_annual_tco2e),
                "emissions_total_ref_period_tco2e": str(rail_result.emissions_total_ref_period_tco2e),
            })
            activity_row.extra_fields = extra
            return rail_result.emissions_total_ref_period_tco2e

        # Tables with their own calculation contract must not fall back to
        # generic quantity × metric multiplication merely because a legacy
        # metric natural key happens to resolve.
        base_table_key = mitigation_base_table_key(activity_row.ui_table_key)
        if base_table_key == "refurbishment":
            return await _recalc_refurbishment_row(db, activity_row)
        if base_table_key in _INDEPENDENT_CALCULATION_TABLES:
            return None
        specialized_calculator = _SPECIALIZED_CALCULATORS.get(base_table_key)
        if specialized_calculator is not None:
            return await specialized_calculator(db, activity_row)

        try:
            qty = Decimal(str(activity_row.quantity))
        except Exception:
            # Validate the user-entered quantity before interpreting an
            # unresolved metric as a dataset gap.
            activity_row._activity_inputs_incomplete = True
            return None
        if not qty.is_finite():
            activity_row._activity_inputs_incomplete = True
            return None

        # 1. Resolve the emission factor metric. ActivityData stores the stable
        # natural key; metric_id is retained only as a legacy compatibility path.
        metric_natural_key = getattr(activity_row, "metric_natural_key", None)
        metric = None
        if metric_natural_key:
            metric = await get_background_grade_metric_by_natural_key(
                db,
                activity_row.dataset_revision_id,
                metric_natural_key,
            )
        else:
            legacy_metric_id = getattr(activity_row, "metric_id", None)
            if legacy_metric_id is not None:
                metric = await get_background_grade_metric_orm(db, legacy_metric_id)

        if metric is None:
            logger.warning(
                "calculate_and_store: no BackgroundGradeMetric resolved for activity_data %s "
                "(natural_key=%r, legacy_metric_id=%r)",
                activity_row.id,
                metric_natural_key,
                getattr(activity_row, "metric_id", None),
            )
            if metric_natural_key or getattr(activity_row, "metric_id", None) is not None:
                from services.project_dataset_recalculation import MissingDatasetDataError

                raise MissingDatasetDataError(
                    "Background grade metrics",
                    "The selected revision does not contain the background grade metric used by this entry.",
                )
            return None

        if metric.value is None:
            logger.info(
                "calculate_and_store: metric %s has no emission factor value; skipping calculation",
                metric.id,
            )
            if raise_errors and getattr(activity_row, "_strict_dataset_recalculation", False):
                from services.project_dataset_recalculation import MissingDatasetDataError

                raise MissingDatasetDataError(
                    "Background grade metrics",
                    "The selected revision contains the matching metric but its emission factor value is missing.",
                )
            return None

        # 2. Calculate
        ef = Decimal(str(metric.value))

        if (
            activity_row.unit_id is not None
            and metric.unit_id is not None
            and activity_row.unit_id != metric.unit_id
        ):
            conv_factor = await get_conversion_factor(
                db,
                activity_row.unit_id,
                metric.unit_id,
                activity_row.dataset_revision_id,
            )
            if conv_factor is None:
                if raise_errors and getattr(activity_row, "_strict_dataset_recalculation", False):
                    from services.project_dataset_recalculation import MissingDatasetDataError

                    raise MissingDatasetDataError(
                        "Unit conversions",
                        "No conversion exists between the entered unit and the selected dataset unit.",
                    )
                logger.warning(
                    "calculate_and_store: no unit conversion found from unit %s to metric unit %s "
                    "for activity_data %s; using raw quantity",
                    activity_row.unit_id,
                    metric.unit_id,
                    activity_row.id,
                )
            else:
                qty = qty * conv_factor

        tco2e = qty * ef

        # 3. Resolve unit — prefer the metric's unit; fall back to the activity row's unit
        result_unit_id: Optional[UUID] = metric.unit_id or activity_row.unit_id

        # 4. Upsert result row
        lc = metric.lifecycle_module_code
        await upsert_result(
            db,
            project_id=activity_row.project_id,
            project_stage_instance_id=activity_row.project_stage_instance_id,
            activity_data_id=activity_row.id,
            value_key=lc or "total",
            lifecycle_module_code=lc,
            value=tco2e,
            unit_id=result_unit_id,
        )

        return tco2e

    except Exception as exc:
        logger.exception(
            "calculate_and_store failed for activity_data %s: %s",
            getattr(activity_row, "id", None),
            exc,
        )
        if raise_errors:
            raise
        try:
            await db.rollback()
        except Exception:
            pass
        return None


async def calculate_and_store(
    db: AsyncSession,
    activity_row: ActivityData,
    *,
    raise_errors: bool = False,
) -> Optional[Decimal]:
    """Calculate a row and synchronize its reportable facts into the result ledger."""
    activity_row_id = activity_row.id
    activity_row._activity_inputs_incomplete = False
    # Replace the row's facts on every recalculation. This prevents result keys
    # from an earlier calculator path from remaining in dashboard totals.
    from models.emissions_results import EmissionsResult

    await db.execute(delete(EmissionsResult).where(EmissionsResult.activity_data_id == activity_row_id))
    result = await _calculate_and_store_impl(db, activity_row, raise_errors=raise_errors)
    # _calculate_and_store_impl rolls back the session when a calculation or
    # result write fails. Do not touch an expired ORM row after that rollback:
    # doing so can trigger an implicit async refresh (MissingGreenlet).
    if not db.in_transaction():
        logger.error(
            "Skipping result-ledger synchronization for activity_data %s because calculation failed",
            activity_row_id,
        )
        return result
    if result is None and (
        _has_dedicated_calculator(activity_row)
        or getattr(activity_row, "_activity_inputs_incomplete", False)
    ):
        # A dedicated calculator returning no result means its required inputs
        # or factors were unavailable. Do not mirror stale client-provided
        # extra_fields into the ledger as though they were calculated values.
        return None
    try:
        from services.result_ledger import persist_legacy_outputs

        await persist_legacy_outputs(db, activity_row)
    except Exception:
        logger.exception("Failed to synchronize result ledger for activity_data %s", activity_row_id)
        if raise_errors:
            raise
        # Keep the shared session usable and make the backfill's transaction
        # check stop immediately instead of continuing in an aborted transaction.
        try:
            await db.rollback()
        except Exception:
            logger.exception("Failed to roll back after ledger synchronization error for %s", activity_row_id)
    return result
