from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
#from sqlalchemy.future import select
from sqlalchemy import select, update as sql_update, func
from models.project_reporting_submission import ProjectReportingSubmission
from schemas.project_reporting_submission import (
    ProjectReportingSubmissionCreate,
    ProjectReportingSubmissionUpdate,
    ConstructionPeriodCreate,
)

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional
from dateutil.relativedelta import relativedelta

from models.project import Project
from models.project_stage_config import ProjectStageConfig, ProjectStage, ReportFrequency
from models.project_reporting_submission import ProjectReportingSubmission
from models.activity_data import ActivityData
from models.project_options import ProjectOption
from models.emissions_results import EmissionsResult


async def create_submission(db: AsyncSession, payload: ProjectReportingSubmissionCreate) -> ProjectReportingSubmission:
    obj = ProjectReportingSubmission(**payload.dict())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_or_create_submission(
    db: AsyncSession,
    project_id: UUID,
    stage_instance_id: UUID,
    period_label: str,
    frequency: str,
    period_start_date: date,
    period_end_date: date,
) -> ProjectReportingSubmission:
    result = await db.execute(
        select(ProjectReportingSubmission).where(
            ProjectReportingSubmission.project_id == project_id,
            ProjectReportingSubmission.period_label == period_label,
            ProjectReportingSubmission.stage_instance_id == stage_instance_id,
        )
    )
    existing = result.scalars().first()
    if existing:
        return existing
    obj = ProjectReportingSubmission(
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        period_label=period_label,
        frequency=frequency,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        status="in_progress",
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_submission(db: AsyncSession, submission_id: UUID) -> ProjectReportingSubmission | None:
    result = await db.execute(
        select(ProjectReportingSubmission).where(
            ProjectReportingSubmission.id == submission_id
        )
    )
    return result.scalars().first()


async def list_submissions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: UUID | None = None,
    is_open: bool | None = None,
) -> list[ProjectReportingSubmission]:
    query = select(ProjectReportingSubmission)
    if project_id:
        query = query.where(ProjectReportingSubmission.project_id == project_id)
    if is_open is not None:
        if is_open:
            query = query.where(ProjectReportingSubmission.status != "approved")
        else:
            query = query.where(ProjectReportingSubmission.status == "approved")
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_submission(
    db: AsyncSession, obj: ProjectReportingSubmission, payload: ProjectReportingSubmissionUpdate
) -> ProjectReportingSubmission:
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    return obj


async def delete_submission(db: AsyncSession, submission_id: UUID) -> bool:
    obj = await get_submission(db, submission_id)
    if obj:
        await db.delete(obj)
        return True
    return False



def _period_iter(start: date, freq: ReportFrequency, periods: int):
    current = date(start.year, start.month, 1)
    for _ in range(periods):
        if freq == ReportFrequency.MONTHLY:
            nxt = current + relativedelta(months=1)
            yield (current, nxt - relativedelta(days=1), f"{current.strftime('%b %Y')}")
            current = nxt
        elif freq == ReportFrequency.QUARTERLY:
            nxt = current + relativedelta(months=3)
            yield (current, nxt - relativedelta(days=1), f"Q{((current.month-1)//3)+1} {current.year}")
            current = nxt
        elif freq == ReportFrequency.BI_MONTHLY:
            nxt = current + relativedelta(months=2)
            yield (current, nxt - relativedelta(days=1), f"{current.strftime('%b %Y')} - {(nxt - relativedelta(days=1)).strftime('%b %Y')}")
            current = nxt
        elif freq == ReportFrequency.ANNUAL:
            nxt = date(current.year + 1, current.month, 1)
            yield (current, nxt - relativedelta(days=1), str(current.year))
            current = nxt
        else:
            break

async def generate_submissions_for_project(db: AsyncSession, project: Project, periods: int = 12):
    sc = (await db.execute(
        select(ProjectStageConfig).where(
            (ProjectStageConfig.project_id == project.id) &
            (ProjectStageConfig.stage == ProjectStage.CONSTRUCTION) &
            (ProjectStageConfig.enabled == True)
        )
    )).scalar_one_or_none()

    if not sc or not sc.frequency:
        if project.project_class.name == "RECURRING" and project.first_submission_month:
            freq = ReportFrequency.MONTHLY
            anchor = date(project.first_submission_month.year, project.first_submission_month.month, 1)
        else:
            return
    else:
        freq = sc.frequency
        if project.first_submission_month:
            anchor = date(project.first_submission_month.year, project.first_submission_month.month, 1)
        elif project.construction_start_date:
            anchor = date(project.construction_start_date.year, project.construction_start_date.month, 1)
        else:
            today = date.today()
            anchor = date(today.year, today.month, 1)

    for start, end, label in _period_iter(anchor, freq, periods):
        exists = (await db.execute(
            select(ProjectReportingSubmission).where(
                (ProjectReportingSubmission.project_id == project.id) &
                (ProjectReportingSubmission.period_label == label)
            )
        )).scalar_one_or_none()
        if exists:
            continue

        db.add(ProjectReportingSubmission(
            project_id=project.id,
            frequency=freq.name,
            period_label=label,
            period_start_date=start,
            period_end_date=end,
            status="in_progress",
        ))
    await db.flush()


async def create_construction_period(
    db: AsyncSession,
    payload: ConstructionPeriodCreate,
) -> ProjectReportingSubmission:
    obj = ProjectReportingSubmission(
        project_id=payload.project_id,
        stage_instance_id=payload.stage_instance_id,
        frequency=payload.frequency,
        period_label=payload.period_label,
        period_start_date=payload.period_start_date,
        period_end_date=payload.period_end_date,
        due_date=payload.due_date,
        status="in_progress",
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def list_construction_periods(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> list[ProjectReportingSubmission]:
    result = await db.execute(
        select(ProjectReportingSubmission)
        .where(ProjectReportingSubmission.stage_instance_id == stage_instance_id)
        .order_by(ProjectReportingSubmission.period_start_date.asc())
    )
    return result.scalars().all()


async def get_construction_period(
    db: AsyncSession,
    period_id: UUID,
) -> Optional[ProjectReportingSubmission]:
    result = await db.execute(
        select(ProjectReportingSubmission).where(ProjectReportingSubmission.id == period_id)
    )
    return result.scalars().first()


async def set_period_status(
    db: AsyncSession,
    period: ProjectReportingSubmission,
    new_status: str,
    **kwargs,
) -> ProjectReportingSubmission:
    period.status = new_status
    for key, value in kwargs.items():
        setattr(period, key, value)
    period.updated_on = datetime.utcnow()
    db.add(period)
    await db.flush()
    await db.refresh(period)
    return period


def _next_period_label(freq: str, period_end_date: date) -> tuple[date, date, str]:
    start = period_end_date + relativedelta(days=1)
    if freq == "MONTHLY":
        end = start + relativedelta(months=1) - relativedelta(days=1)
        label = start.strftime("%b %Y")
    elif freq == "QUARTERLY":
        end = start + relativedelta(months=3) - relativedelta(days=1)
        label = f"Q{((start.month - 1) // 3) + 1} {start.year}"
    elif freq == "BI_MONTHLY":
        end = start + relativedelta(months=2) - relativedelta(days=1)
        label = f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"
    elif freq == "ANNUAL":
        end = date(start.year + 1, start.month, 1) - relativedelta(days=1)
        label = str(start.year)
    else:
        end = start + relativedelta(months=1) - relativedelta(days=1)
        label = start.strftime("%b %Y")
    return start, end, label


async def auto_create_next_period(
    db: AsyncSession,
    approved_period: ProjectReportingSubmission,
) -> ProjectReportingSubmission:
    start, end, label = _next_period_label(approved_period.frequency, approved_period.period_end_date)

    existing = (await db.execute(
        select(ProjectReportingSubmission).where(
            (ProjectReportingSubmission.stage_instance_id == approved_period.stage_instance_id) &
            (ProjectReportingSubmission.period_label == label)
        )
    )).scalars().first()
    if existing:
        return existing

    next_period = ProjectReportingSubmission(
        project_id=approved_period.project_id,
        stage_instance_id=approved_period.stage_instance_id,
        frequency=approved_period.frequency,
        period_label=label,
        period_start_date=start,
        period_end_date=end,
        status="in_progress",
    )
    db.add(next_period)
    await db.flush()
    await db.refresh(next_period)
    return next_period


async def seed_first_period(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> Optional[ProjectReportingSubmission]:
    from models.project_stage_instances import ProjectStageInstance
    from models.project import Project
    from models.project_stage_config import ProjectStageConfig, ProjectStage
    from models.activity_data import ActivityData

    stage_inst = (await db.execute(
        select(ProjectStageInstance).where(ProjectStageInstance.id == stage_instance_id)
    )).scalars().first()
    if not stage_inst:
        return None

    project = (await db.execute(
        select(Project).where(Project.id == stage_inst.project_id)
    )).scalars().first()
    if not project:
        return None

    stage_config = (await db.execute(
        select(ProjectStageConfig).where(
            (ProjectStageConfig.project_id == stage_inst.project_id) &
            (ProjectStageConfig.stage == ProjectStage.CONSTRUCTION)
        )
    )).scalars().first()

    freq = stage_config.frequency.value if stage_config and stage_config.frequency else "MONTHLY"

    anchor_date = (
        project.first_submission_month
        or project.construction_start_date
        or date.today().replace(day=1)
    )
    anchor = date(anchor_date.year, anchor_date.month, 1)

    existing_periods = (await db.execute(
        select(ProjectReportingSubmission)
        .where(ProjectReportingSubmission.stage_instance_id == stage_instance_id)
        .order_by(ProjectReportingSubmission.period_start_date)
    )).scalars().all()

    approval_status = getattr(stage_inst, 'approval_status', None)
    created_new = None

    if approval_status == 'final_approved':
        anchor_start, anchor_end, anchor_label = _next_period_label(freq, anchor - relativedelta(days=1))

        legacy_period = next(
            (p for p in existing_periods if p.period_label == anchor_label),
            None
        )
        if not legacy_period:
            orphan_count = (await db.execute(
                select(func.count(ActivityData.id)).where(
                    (ActivityData.project_stage_instance_id == stage_instance_id) &
                    (ActivityData.ui_table_key.in_(["constructionG2", "constructionG3"])) &
                    (ActivityData.submission_period_id == None)
                )
            )).scalar() or 0

            if orphan_count > 0:
                legacy_period = ProjectReportingSubmission(
                    project_id=stage_inst.project_id,
                    stage_instance_id=stage_instance_id,
                    frequency=freq,
                    period_label=anchor_label,
                    period_start_date=anchor_start,
                    period_end_date=anchor_end,
                    status="approved",
                )
                db.add(legacy_period)
                await db.flush()
                await db.refresh(legacy_period)

                await db.execute(
                    sql_update(ActivityData)
                    .where(
                        (ActivityData.project_stage_instance_id == stage_instance_id) &
                        (ActivityData.ui_table_key.in_(["constructionG2", "constructionG3"])) &
                        (ActivityData.submission_period_id == None)
                    )
                    .values(submission_period_id=legacy_period.id)
                )

        has_in_progress = any(p.status == "in_progress" for p in existing_periods)
        if not has_in_progress:
            next_start, next_end, next_label = _next_period_label(freq, anchor_end)
            dup = next((p for p in existing_periods if p.period_label == next_label), None)
            if not dup:
                new_period = ProjectReportingSubmission(
                    project_id=stage_inst.project_id,
                    stage_instance_id=stage_instance_id,
                    frequency=freq,
                    period_label=next_label,
                    period_start_date=next_start,
                    period_end_date=next_end,
                    status="in_progress",
                )
                db.add(new_period)
                await db.flush()
                await db.refresh(new_period)
                created_new = new_period

    else:
        if not existing_periods:
            start, end, label = _next_period_label(freq, anchor - relativedelta(days=1))
            dup = (await db.execute(
                select(ProjectReportingSubmission).where(
                    (ProjectReportingSubmission.stage_instance_id == stage_instance_id) &
                    (ProjectReportingSubmission.period_label == label)
                )
            )).scalars().first()
            if not dup:
                new_period = ProjectReportingSubmission(
                    project_id=stage_inst.project_id,
                    stage_instance_id=stage_instance_id,
                    frequency=freq,
                    period_label=label,
                    period_start_date=start,
                    period_end_date=end,
                    status="in_progress",
                )
                db.add(new_period)
                await db.flush()
                await db.refresh(new_period)
                created_new = new_period
        elif not any(p.status == "in_progress" for p in existing_periods):
            # All existing periods are approved/rejected — ensure the next in_progress period exists.
            # This acts as a safety net if auto_create_next_period failed silently during approval.
            last_approved = max(
                (p for p in existing_periods if p.status == "approved"),
                key=lambda p: p.period_end_date,
                default=None,
            )
            if last_approved:
                nxt_start, nxt_end, nxt_label = _next_period_label(
                    last_approved.frequency, last_approved.period_end_date
                )
                dup = next((p for p in existing_periods if p.period_label == nxt_label), None)
                if not dup:
                    new_period = ProjectReportingSubmission(
                        project_id=stage_inst.project_id,
                        stage_instance_id=stage_instance_id,
                        frequency=last_approved.frequency,
                        period_label=nxt_label,
                        period_start_date=nxt_start,
                        period_end_date=nxt_end,
                        status="in_progress",
                    )
                    db.add(new_period)
                    await db.flush()
                    await db.refresh(new_period)
                    created_new = new_period

    return created_new


async def get_emissions_by_period_ids(
    db: AsyncSession,
    period_ids: list[UUID],
) -> Dict[UUID, Decimal]:
    if not period_ids:
        return {}

    rows = (await db.execute(
        select(
            ActivityData.submission_period_id,
            func.coalesce(func.sum(EmissionsResult.value), 0).label("total"),
        )
        .join(EmissionsResult, EmissionsResult.activity_data_id == ActivityData.id)
        .outerjoin(ProjectOption, ProjectOption.id == ActivityData.project_option_id)
        .where(ActivityData.submission_period_id.in_(period_ids))
        .where(ActivityData.ui_table_key.in_(["constructionG2", "constructionG3", "electricity", "recurringG3", "completeness"]))
        .where(EmissionsResult.reporting_measure.in_(["actual", "mitigation", "baseline_adjustment"]))
        .where(EmissionsResult.is_supplementary.is_(False))
        .where(EmissionsResult.accounting_basis.in_(["common", "location"]))
        .where(
            (ActivityData.project_option_id == None) | (ProjectOption.is_default == True)
        )
        .group_by(ActivityData.submission_period_id)
    )).all()
    totals = {row.submission_period_id: Decimal(str(row.total)) for row in rows}
    return totals


async def get_total_construction_emissions(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> Decimal:

    row = (await db.execute(
        select(func.coalesce(func.sum(EmissionsResult.value), 0).label("total"))
        .select_from(ActivityData)
        .join(EmissionsResult, EmissionsResult.activity_data_id == ActivityData.id)
        .join(
            ProjectReportingSubmission,
            ProjectReportingSubmission.id == ActivityData.submission_period_id,
        )
        .outerjoin(ProjectOption, ProjectOption.id == ActivityData.project_option_id)
        .where(ProjectReportingSubmission.stage_instance_id == stage_instance_id)
        .where(ActivityData.ui_table_key.in_(["constructionG2", "constructionG3", "electricity", "recurringG3", "completeness"]))
        .where(EmissionsResult.reporting_measure.in_(["actual", "mitigation", "baseline_adjustment"]))
        .where(EmissionsResult.is_supplementary.is_(False))
        .where(EmissionsResult.accounting_basis.in_(["common", "location"]))
        .where(
            (ActivityData.project_option_id == None) | (ProjectOption.is_default == True)
        )
    )).first()
    construction_total = Decimal(str(row.total)) if row else Decimal(0)
    return construction_total
