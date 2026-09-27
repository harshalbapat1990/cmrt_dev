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

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
from services.grade34_activity_emissions import recalc_grade34_construction_activity_row
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
from services.ui_table_key_normalization import matches_base_table_key
from services.maintenance_replacement_component_level_calcs import (
    MaintenanceCalcRequest,
    calculator as maintenance_calculator,
)

logger = logging.getLogger(__name__)


async def _calculate_and_store_impl(
    db: AsyncSession,
    activity_row: ActivityData,
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
            # Refurbishment rows: delegate entirely to MaintenanceReplacementCalculator
            if matches_base_table_key(activity_row.ui_table_key, "refurbishment"):
                extra = activity_row.extra_fields or {}
                mr_factor_id = extra.get("mr_factor_id")
                if mr_factor_id:
                    factor_q = await db.execute(
                        select(MaintenanceReplacementFactor).where(
                            MaintenanceReplacementFactor.id == mr_factor_id
                        )
                    )
                    factor = factor_q.scalars().first()

                    jur_q = await db.execute(
                        select(Jurisdiction).where(Jurisdiction.id == factor.jurisdiction_id)
                    ) if factor and factor.jurisdiction_id else None
                    jur = jur_q.scalars().first() if jur_q else None
                    jurisdiction_name = jur.name if jur else "Australia"

                    project_q = await db.execute(
                        select(Project).where(Project.id == activity_row.project_id)
                    )
                    project = project_q.scalars().first()
                    reference_period = float(project.operational_life_years) if project and project.operational_life_years else None
                    frequency_years = float(extra.get("frequency", 0) or 0)

                    if factor and reference_period and frequency_years > 0:
                        calc_quantity = float(activity_row.quantity)
                        if (
                            activity_row.unit_id is not None
                            and factor.unit_id is not None
                            and activity_row.unit_id != factor.unit_id
                        ):
                            conv = await get_conversion_factor(
                                db, activity_row.unit_id, factor.unit_id
                            )
                            if conv is not None:
                                calc_quantity = calc_quantity * float(conv)
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
                        tco2e = Decimal(str(calc_result.total_emissions_tco2e))
                        await upsert_result(
                            db,
                            project_id=activity_row.project_id,
                            project_stage_instance_id=activity_row.project_stage_instance_id,
                            activity_data_id=activity_row.id,
                            value_key="B2-5",
                            lifecycle_module_code="B2-5",
                            value=tco2e,
                            unit_id=activity_row.unit_id,
                        )
                        await upsert_result(
                            db,
                            project_id=activity_row.project_id,
                            project_stage_instance_id=activity_row.project_stage_instance_id,
                            activity_data_id=activity_row.id,
                            value_key="scope3",
                            lifecycle_module_code=None,
                            is_supplementary=True,
                            value=tco2e,
                            unit_id=activity_row.unit_id,
                        )
                        return tco2e
                    
            asset_total = await recalc_asset_row(db, activity_row)
            if asset_total is not None:
                return asset_total

            grade2_component_total = await recalc_grade2_component_row(db, activity_row)
            if grade2_component_total is not None:
                return grade2_component_total

            grade2_b4_total = await recalc_grade2_b4_replacement_row(db, activity_row)
            if grade2_b4_total is not None:
                return grade2_b4_total

            repl_detailed_total = await recalc_detailed_b2b5_row(db, activity_row)
            if repl_detailed_total is not None:
                return repl_detailed_total

            op_total = await recalc_operational_row(db, activity_row)
            if op_total is not None:
                return op_total

            op_fw_total = await recalc_operational_fuel_water_row(db, activity_row)
            if op_fw_total is not None:
                return op_fw_total

            shortcut_total = await recalc_shortcut_is_materials_row(db, activity_row)
            if shortcut_total is not None:
                return shortcut_total

            inuse_gases_total = await recalc_inuse_gases_row(db, activity_row)
            if inuse_gases_total is not None:
                return inuse_gases_total

            use_b1g3_total = await recalc_use_b1g3_row(db, activity_row)
            if use_b1g3_total is not None:
                return use_b1g3_total

            concrete_total = await recalc_concrete_row(db, activity_row)
            if concrete_total is not None:
                return concrete_total

            grade34_total = await recalc_grade34_construction_activity_row(db, activity_row)
            if grade34_total is not None:
                return grade34_total

            electricity_total = await recalc_electricity_activity_row(db, activity_row)
            if electricity_total is not None:
                return electricity_total

            logger.warning(
                "calculate_and_store: no BackgroundGradeMetric resolved for activity_data %s "
                "(natural_key=%r, legacy_metric_id=%r)",
                activity_row.id,
                metric_natural_key,
                getattr(activity_row, "metric_id", None),
            )
            return None

        if metric.value is None:
            logger.info(
                "calculate_and_store: metric %s has no emission factor value; skipping calculation",
                metric.id,
            )
            return None

        # 2. Calculate
        ef = Decimal(str(metric.value))
        qty = Decimal(str(activity_row.quantity))

        if (
            activity_row.unit_id is not None
            and metric.unit_id is not None
            and activity_row.unit_id != metric.unit_id
        ):
            conv_factor = await get_conversion_factor(
                db, activity_row.unit_id, metric.unit_id
            )
            if conv_factor is None:
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
            "calculate_and_store failed for activity_data %s: %s", activity_row.id, exc
        )
        try:
            await db.rollback()
        except Exception:
            pass
        return None


async def calculate_and_store(
    db: AsyncSession,
    activity_row: ActivityData,
) -> Optional[Decimal]:
    """Calculate a row and synchronize its reportable facts into the result ledger."""
    activity_row_id = activity_row.id
    result = await _calculate_and_store_impl(db, activity_row)
    # _calculate_and_store_impl rolls back the session when a calculation or
    # result write fails. Do not touch an expired ORM row after that rollback:
    # doing so can trigger an implicit async refresh (MissingGreenlet).
    if not db.in_transaction():
        logger.error(
            "Skipping result-ledger synchronization for activity_data %s because calculation failed",
            activity_row_id,
        )
        return result
    try:
        from services.result_ledger import persist_legacy_outputs

        await persist_legacy_outputs(db, activity_row)
    except Exception:
        logger.exception("Failed to synchronize result ledger for activity_data %s", activity_row_id)
        # Keep the shared session usable and make the backfill's transaction
        # check stop immediately instead of continuing in an aborted transaction.
        try:
            await db.rollback()
        except Exception:
            logger.exception("Failed to roll back after ledger synchronization error for %s", activity_row_id)
    return result
