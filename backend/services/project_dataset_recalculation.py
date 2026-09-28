"""Recalculate a project's emissions against its newly selected dataset revision."""
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from models.emissions_results import EmissionsResult
from models.maintenance_replacement_factors import MaintenanceReplacementFactor
from models.project import Project
from models.project_stage_instances import ProjectStageInstance
from services.emissions_calculator import calculate_and_store


class MissingDatasetDataError(Exception):
    """A required record is absent from the selected published dataset."""

    def __init__(self, dataset_table: str, message: str | None = None):
        self.dataset_table = dataset_table
        super().__init__(message or f"Required data is missing from {dataset_table}.")


class ProjectDatasetRecalculationError(Exception):
    """Raised when any row fails technically; caller must roll back the switch."""

    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__("One or more entries could not be recalculated.")


_DATASET_TABLE_BY_ACTIVITY = {
    "asset": "Background grade metrics / asset factors",
    "component": "Grade 2 component factors",
    "constructionG2": "Grade 2 construction factors",
    "constructionG3": "Grade 3 construction factors",
    "bcDetailedLevel": "Grade 3/4 detailed level factors",
    "concreteRegSimplified": "Concrete mix and emissions factor tables",
    "concreteRegDetailed": "Concrete mix and emissions factor tables",
    "electricity": "Electricity detailed factors",
    "opEnergyElectricity": "Electricity detailed factors",
    "refurbishment": "Maintenance replacement factors",
    "componentRepl": "Maintenance replacement factors",
    "replDetailed": "Maintenance replacement factors",
}


def _entry_label(row: ActivityData) -> str:
    extra = row.extra_fields or {}
    for field in ("emissions_source_name", "emissions_source", "item", "name", "label"):
        value = extra.get(field)
        if value:
            return str(value)
    key = row.ui_table_key or "data entry"
    return key.replace("-", " ").replace("_", " ").strip().title()


def _missing_dataset_table(row: ActivityData) -> str:
    key = (row.ui_table_key or "").split("-mitigation", 1)[0]
    return _DATASET_TABLE_BY_ACTIVITY.get(key, "Background grade metrics and related factor tables")


def _warning_dataset_table(warnings: list[str], row: ActivityData) -> str:
    for warning in warnings:
        for marker in (" in ", " from "):
            if marker in warning:
                candidate = warning.split(marker, 1)[1].split(" for ", 1)[0].strip()
                if candidate and ("_" in candidate or candidate.lower().startswith(("grade ", "background "))):
                    return candidate
    return _missing_dataset_table(row)


async def recalculate_project_for_revision(
    db: AsyncSession,
    project_id: UUID,
    dataset_revision_id: UUID,
) -> dict[str, Any]:
    """Recalculate project results under a tentative revision binding.

    Missing dataset records are replaced with zero and reported. Technical errors
    are collected and raised after the full pass so the route can roll back the
    binding and every result change atomically.
    """
    result = await db.execute(
        select(ActivityData)
        .where(ActivityData.project_id == project_id)
        .order_by(ActivityData.created_at, ActivityData.id)
    )
    rows = list(result.scalars().all())
    missing: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    missing_replacement_factor_rows: set[UUID] = set()

    # Rewrite row bindings and saved revision-specific factor references before
    # deriving automatic mitigation rows, so those rows inherit the new revision.
    for row in rows:
        row.dataset_revision_id = dataset_revision_id
        extra = dict(row.extra_fields or {})
        mr_factor_id = extra.get("mr_factor_id")
        if mr_factor_id:
            try:
                old_factor_id = UUID(str(mr_factor_id))
            except (TypeError, ValueError):
                old_factor_id = None
            old_factor = await db.get(MaintenanceReplacementFactor, old_factor_id) if old_factor_id else None
            if old_factor is not None:
                replacement = (await db.execute(
                    select(MaintenanceReplacementFactor).where(
                        MaintenanceReplacementFactor.dataset_revision_id == dataset_revision_id,
                        MaintenanceReplacementFactor.jurisdiction_id == old_factor.jurisdiction_id,
                        MaintenanceReplacementFactor.activity_type == old_factor.activity_type,
                        MaintenanceReplacementFactor.item == old_factor.item,
                    ).limit(1)
                )).scalars().first()
                extra["mr_factor_id"] = str(replacement.id) if replacement else None
                row.extra_fields = extra
                if replacement is None:
                    missing_replacement_factor_rows.add(row.id)
            else:
                extra["mr_factor_id"] = None
                row.extra_fields = extra
                missing_replacement_factor_rows.add(row.id)

    # Rebuild automatic mitigations from source inputs under the selected
    # revision. Existing generated rows are replaced by the sync services.
    from crud.project import get_project
    from services.auto_electricity_mitigation import (
        AUTO_ELECTRICITY_TABLE_KEYS,
        sync_auto_electricity_for_table,
    )
    from services.auto_substitution_mitigation import (
        AUTO_SUBSTITUTION_TABLE_KEYS,
        sync_auto_substitution_for_source_row,
    )

    project = await get_project(db, project_id)
    synced_electricity_buckets: set[tuple[UUID, str, Any, Any]] = set()
    for row in rows:
        if row.project_mitigation_id is not None:
            continue
        try:
            stage_instance = await db.get(ProjectStageInstance, row.project_stage_instance_id)
            if stage_instance is None:
                continue
            async with db.begin_nested():
                if row.ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
                    await sync_auto_substitution_for_source_row(
                        db, row, stage_instance, project=project
                    )
                if row.ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS:
                    bucket = (
                        stage_instance.id,
                        row.ui_table_key,
                        row.project_option_id,
                        row.submission_period_id,
                    )
                    if bucket not in synced_electricity_buckets:
                        await sync_auto_electricity_for_table(
                            db,
                            stage_instance,
                            row.ui_table_key,
                            row.project_option_id,
                            row.submission_period_id,
                            project=project,
                        )
                        synced_electricity_buckets.add(bucket)
        except Exception as exc:
            errors.append({
                "activity_data_id": str(row.id),
                "entry": _entry_label(row),
                "data_entry_table": row.ui_table_key,
                "message": f"Could not rebuild automatic mitigation: {exc}",
            })

    # Sync may have created, changed, or removed mitigation rows. Re-read the
    # complete activity set and calculate each surviving row exactly once.
    rows = list((await db.execute(
        select(ActivityData)
        .where(ActivityData.project_id == project_id)
        .order_by(ActivityData.created_at, ActivityData.id)
    )).scalars().all())
    for row in rows:
        row.dataset_revision_id = dataset_revision_id
        if row.ui_table_key == "completeness":
            continue
        row._dataset_data_warnings = []
        row._strict_dataset_recalculation = True
        try:
            extra = dict(row.extra_fields or {})
            if row.id in missing_replacement_factor_rows:
                raise MissingDatasetDataError("Maintenance replacement factors")
            mr_factor_id = extra.get("mr_factor_id")
            if mr_factor_id:
                try:
                    factor_id = UUID(str(mr_factor_id))
                except (TypeError, ValueError):
                    factor_id = None
                factor = await db.get(MaintenanceReplacementFactor, factor_id) if factor_id else None
                if factor is None or factor.dataset_revision_id != dataset_revision_id:
                    raise MissingDatasetDataError("Maintenance replacement factors")

            async with db.begin_nested():
                await db.execute(delete(EmissionsResult).where(EmissionsResult.activity_data_id == row.id))
                await db.flush()
                await calculate_and_store(db, row, raise_errors=True)
                emitted = (await db.execute(
                    select(EmissionsResult.id).where(EmissionsResult.activity_data_id == row.id).limit(1)
                )).scalar_one_or_none()
                warnings = getattr(row, "_dataset_data_warnings", []) or []
                if warnings:
                    warning_text = "; ".join(map(str, warnings))
                    raise MissingDatasetDataError(
                        _warning_dataset_table(list(map(str, warnings)), row),
                        warning_text,
                    )
                if emitted is None and getattr(row, "metric_natural_key", None):
                    raise MissingDatasetDataError(_missing_dataset_table(row))
        except MissingDatasetDataError as exc:
            await db.execute(delete(EmissionsResult).where(EmissionsResult.activity_data_id == row.id))
            if (row.ui_table_key or "").split("-mitigation", 1)[0] in {"railUsers", "largeRailUsers"}:
                await db.execute(delete(EmissionsResult).where(
                    EmissionsResult.activity_data_id.is_(None),
                    EmissionsResult.assessment_year.is_not(None),
                    EmissionsResult.value_key.like(f"b8_rail_{row.id.hex}_%"),
                ))
                extra.update({
                    "emissions_intensity_tco2e_kl": "0",
                    "emissions_annual_tco2e": "0",
                    "emissions_total_ref_period_tco2e": "0",
                })
                row.extra_fields = extra
                from services.result_ledger import _persist_annual_rail_results

                await _persist_annual_rail_results(db, row, extra)
            await upsert_result(
                db,
                project_id=row.project_id,
                project_stage_instance_id=row.project_stage_instance_id,
                activity_data_id=row.id,
                value_key="total",
                lifecycle_module_code=row.lifecycle_module_code,
                value=0,
                unit_id=row.unit_id,
            )
            missing.append({
                "activity_data_id": str(row.id),
                "entry": _entry_label(row),
                "data_entry_table": row.ui_table_key,
                "dataset_table": exc.dataset_table,
                "message": str(exc),
            })
        except Exception as exc:
            errors.append({
                "activity_data_id": str(row.id),
                "entry": _entry_label(row),
                "data_entry_table": row.ui_table_key,
                "message": str(exc),
            })
    try:
        from services.annual_road_revision_recalculation import recalculate_annual_road_results

        annual_report = await recalculate_annual_road_results(db, project_id)
        missing.extend(annual_report["missing_data"])
        errors.extend(annual_report["calculation_errors"])
    except Exception as exc:
        errors.append({
            "activity_data_id": None,
            "entry": "Annual road user emissions",
            "data_entry_table": "roadUsers / largeRoadUsers",
            "message": str(exc),
        })

    report = {
        "missing_data": missing,
        "calculation_errors": errors,
        "recalculated_count": len(rows),
    }
    if errors:
        raise ProjectDatasetRecalculationError(report)
    return report
