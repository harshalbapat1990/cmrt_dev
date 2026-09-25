from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.activity_data import ActivityData
from crud.background_grade_metrics import (
    background_grade_metric_to_natural_key,
    get_background_grade_metric_by_natural_key,
    get_background_grade_metric_orm,
)
from models.emissions_results import EmissionsResult
from models.project_reporting_submission import ProjectReportingSubmission
from schemas.activity_data import ActivityDataCreate, ActivityDataOut, ActivityDataUpdate


async def _activity_data_model_kwargs(
    db: AsyncSession,
    payload: ActivityDataCreate,
) -> dict:
    data = payload.model_dump(exclude={"metric_id"})
    legacy_metric_id = payload.metric_id

    if data.get("metric_natural_key") is None and legacy_metric_id is not None:
        metric = await get_background_grade_metric_orm(db, legacy_metric_id)
        if metric is not None:
            data["metric_natural_key"] = background_grade_metric_to_natural_key(metric)
            if data.get("dataset_revision_id") is None:
                data["dataset_revision_id"] = metric.dataset_revision_id

    return data


async def _activity_data_update_kwargs(
    db: AsyncSession,
    obj: ActivityData,
    patch: ActivityDataUpdate,
) -> dict:
    data = patch.model_dump(exclude_unset=True, exclude={"metric_id"})
    legacy_metric_id = patch.metric_id

    if data.get("metric_natural_key") is None and legacy_metric_id is not None:
        metric = await get_background_grade_metric_orm(db, legacy_metric_id)
        if metric is not None:
            data["metric_natural_key"] = background_grade_metric_to_natural_key(metric)
            if data.get("dataset_revision_id") is None:
                data["dataset_revision_id"] = metric.dataset_revision_id

    return data


async def create_activity_data(db: AsyncSession, payload: ActivityDataCreate) -> ActivityData:
    data = await _activity_data_model_kwargs(db, payload)
    obj = ActivityData(**data)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_activity_data(db: AsyncSession, row_id: UUID) -> Optional[ActivityData]:
    result = await db.execute(select(ActivityData).where(ActivityData.id == row_id))
    return result.scalars().first()


async def list_activity_data(
    db: AsyncSession,
    stage_instance_id: UUID,
    ui_table_key: str,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
    project_mitigation_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[ActivityData]:
    q = select(ActivityData).where(
        ActivityData.project_stage_instance_id == stage_instance_id,
        ActivityData.ui_table_key == ui_table_key,
    )
    if project_option_id is not None:
        q = q.where(ActivityData.project_option_id == project_option_id)
    if submission_period_id is not None:
        q = q.where(ActivityData.submission_period_id == submission_period_id)
    if project_mitigation_id is not None:
        q = q.where(ActivityData.project_mitigation_id == project_mitigation_id)
    q = q.order_by(ActivityData.created_at).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def update_activity_data(
    db: AsyncSession, row_id: UUID, patch: ActivityDataUpdate
) -> Optional[ActivityData]:
    obj = await get_activity_data(db, row_id)
    if not obj:
        return None
    update_data = await _activity_data_update_kwargs(db, obj, patch)
    for k, v in update_data.items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_activity_data(db: AsyncSession, row_id: UUID) -> bool:
    obj = await get_activity_data(db, row_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.flush()
    return True


async def bulk_upsert_activity_data(
    db: AsyncSession,
    stage_instance_id: UUID,
    ui_table_key: str,
    rows: List[ActivityDataCreate],
    project_mitigation_id: Optional[UUID] = None,
    replace_option_id: Optional[UUID] = None,
    replace_submission_period_id: Optional[UUID] = None,
) -> List[ActivityData]:
    if project_mitigation_id is not None:
        q_del = select(ActivityData).where(
            ActivityData.project_stage_instance_id == stage_instance_id,
            ActivityData.ui_table_key == ui_table_key,
            ActivityData.project_mitigation_id == project_mitigation_id,
        )
        for ex in (await db.execute(q_del)).scalars().all():
            await db.delete(ex)
    else:
        #option_ids = {r.project_option_id for r in rows}
        #for opt_id in option_ids:
        scopes = {(r.project_option_id, r.submission_period_id) for r in rows}
        if not scopes and replace_option_id is not None:
            scopes = {(replace_option_id, replace_submission_period_id)}
        for opt_id, period_id in scopes:
            q = select(ActivityData).where(
                ActivityData.project_stage_instance_id == stage_instance_id,
                ActivityData.ui_table_key == ui_table_key,
                #ActivityData.project_option_id == opt_id,
                ActivityData.project_mitigation_id.is_(None),
            )
            if opt_id is not None:
                q = q.where(ActivityData.project_option_id == opt_id)
            else:
                q = q.where(ActivityData.project_option_id.is_(None))
            if period_id is not None:
                q = q.where(ActivityData.submission_period_id == period_id)
            else:
                q = q.where(ActivityData.submission_period_id.is_(None))
            existing = (await db.execute(q)).scalars().all()
            for ex in existing:
                await db.delete(ex)
    await db.flush()

    created: List[ActivityData] = []
    for row_payload in rows:
        data = await _activity_data_model_kwargs(db, row_payload)
        obj = ActivityData(**data)
        db.add(obj)
        created.append(obj)
    await db.flush()
    for obj in created:
        await db.refresh(obj)
    return created


async def enrich_with_emissions(
    db: AsyncSession, activity_row: ActivityData
) -> ActivityDataOut:
    q = select(EmissionsResult).where(
        EmissionsResult.activity_data_id == activity_row.id,
        EmissionsResult.is_supplementary == False,
    )
    results = (await db.execute(q)).scalars().all()
    total = sum(r.value for r in results) if results else None
    out = ActivityDataOut.model_validate(activity_row)
    if activity_row.metric_natural_key:
        metric = await get_background_grade_metric_by_natural_key(
            db,
            activity_row.dataset_revision_id,
            activity_row.metric_natural_key,
        )
        out.metric_id = metric.id if metric is not None else None
    out.emissions_tco2e = Decimal(total) if total is not None else None
    return out


async def copy_option_data(
    db: AsyncSession,
    source_option_id: UUID,
    target_option_id: UUID,
) -> int:
    target_rows_q = select(ActivityData).where(
        ActivityData.project_option_id == target_option_id
    )
    for row in (await db.execute(target_rows_q)).scalars().all():
        await db.delete(row)
    await db.flush()

    source_rows_q = select(ActivityData).where(
        ActivityData.project_option_id == source_option_id
    )
    source_rows = (await db.execute(source_rows_q)).scalars().all()

    import uuid as _uuid
    for row in source_rows:
        new_row = ActivityData(
            id=_uuid.uuid4(),
            project_id=row.project_id,
            project_stage_instance_id=row.project_stage_instance_id,
            project_option_id=target_option_id,
            dataset_revision_id=row.dataset_revision_id,
            metric_natural_key=row.metric_natural_key,
            quantity=row.quantity,
            unit_id=row.unit_id,
            ui_table_key=row.ui_table_key,
            extra_fields=row.extra_fields,
        )
        db.add(new_row)

    await db.flush()
    return len(source_rows)


# Table keys that represent the three ops substages synced from Design → Construction
OPS_TABLE_KEYS = [
    "useB1G2", "useB1G3",
    "componentRepl", "refurbishment", "replDetailed",
    "opEnergy", "opEnergyDetailed", "opEnergyElectricity",
]


async def seed_from_design(
    db: AsyncSession,
    design_option_id: UUID,
    construction_stage_instance_id: UUID,
    period_ids: List[UUID],
) -> int:
    """Copy Design ops-substage rows into each Construction period, replacing existing seeded rows."""
    import uuid as _uuid

    # Filter to only editable periods (in_progress or rejected)
    eligible_q = select(ProjectReportingSubmission).where(
        ProjectReportingSubmission.id.in_(period_ids),
        ProjectReportingSubmission.status.in_(("in_progress", "rejected")),
    )
    eligible_periods = (await db.execute(eligible_q)).scalars().all()
    period_ids = [p.id for p in eligible_periods]
    if not period_ids:
        return 0

    # Fetch source rows from the Design option (all 8 ops table keys)
    source_rows_q = select(ActivityData).where(
        ActivityData.project_option_id == design_option_id,
        ActivityData.ui_table_key.in_(OPS_TABLE_KEYS),
    )
    source_rows = (await db.execute(source_rows_q)).scalars().all()

    # Delete existing rows in the target Construction stage for these table keys + periods
    for period_id in period_ids:
        del_q = select(ActivityData).where(
            ActivityData.project_stage_instance_id == construction_stage_instance_id,
            ActivityData.submission_period_id == period_id,
            ActivityData.ui_table_key.in_(OPS_TABLE_KEYS),
        )
        for ex in (await db.execute(del_q)).scalars().all():
            await db.delete(ex)
    await db.flush()

    # Insert copies scoped to each Construction period
    total = 0
    for period_id in period_ids:
        for row in source_rows:
            new_row = ActivityData(
                id=_uuid.uuid4(),
                project_id=row.project_id,
                project_stage_instance_id=construction_stage_instance_id,
                project_option_id=None,
                submission_period_id=period_id,
                dataset_revision_id=row.dataset_revision_id,
                metric_natural_key=row.metric_natural_key,
                quantity=row.quantity,
                unit_id=row.unit_id,
                ui_table_key=row.ui_table_key,
                extra_fields=row.extra_fields,
            )
            db.add(new_row)
            total += 1
    await db.flush()
    return total