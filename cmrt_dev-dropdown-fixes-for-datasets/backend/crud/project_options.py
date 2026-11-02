from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import select

from models.activity_data import ActivityData
from models.project_options import ProjectOption
from models.project_stage_instances import ProjectStageInstance
from models.emissions_results import EmissionsResult
from schemas.project_options import ProjectOptionCreate


_STAGE_ENUM_TO_LABEL: dict = {
    "BUSINESS_CASE": "Business case",
    "DESIGN": "Design",
    "CONSTRUCTION": "Construction",
}


async def create_project_option(db: AsyncSession, payload: ProjectOptionCreate) -> ProjectOption:
    obj = ProjectOption(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_project_option(db: AsyncSession, option_id: UUID) -> Optional[ProjectOption]:
    result = await db.execute(select(ProjectOption).where(ProjectOption.id == option_id))
    return result.scalars().first()


async def list_project_options(
    db: AsyncSession,
    project_id: UUID,
    stage_instance_id: UUID,
    report_number: Optional[int] = None,
) -> List[ProjectOption]:
    q = (
        select(ProjectOption)
        .where(
            ProjectOption.project_id == project_id,
            ProjectOption.stage_instance_id == stage_instance_id,
        )
        .order_by(ProjectOption.report_number, ProjectOption.option_number)
    )
    if report_number is not None:
        q = q.where(ProjectOption.report_number == report_number)
    result = await db.execute(q)
    return result.scalars().all()


async def get_or_create_options_for_stage(
    db: AsyncSession,
    stage_instance: ProjectStageInstance,
) -> List[ProjectOption]:
    n = stage_instance.num_reports_required or 1
    stage_label = _STAGE_ENUM_TO_LABEL.get(stage_instance.stage.value if hasattr(stage_instance.stage, 'value') else str(stage_instance.stage), "Option")
    existing = await list_project_options(db, stage_instance.project_id, stage_instance.id)

    existing_pairs = {(o.report_number, o.option_number) for o in existing}

    for report_num in range(1, n + 1):
        if (report_num, 1) not in existing_pairs:
            new_opt = ProjectOption(
                project_id=stage_instance.project_id,
                stage_instance_id=stage_instance.id,
                report_number=report_num,
                option_number=1,
                label=f"{stage_label} - option 1",
                is_default=True,
            )
            db.add(new_opt)

    await db.flush()
    return await list_project_options(db, stage_instance.project_id, stage_instance.id)


async def create_sub_option(
    db: AsyncSession,
    project_id: UUID,
    stage_instance_id: UUID,
    report_number: int,
    label: str,
) -> ProjectOption:
    q = (
        select(ProjectOption)
        .where(
            ProjectOption.stage_instance_id == stage_instance_id,
            ProjectOption.report_number == report_number,
        )
        .order_by(ProjectOption.option_number.desc())
    )
    last = (await db.execute(q)).scalars().first()
    next_num = (last.option_number + 1) if last else 1

    obj = ProjectOption(
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        report_number=report_number,
        option_number=next_num,
        label=label,
        is_default=False,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def rename_project_option(
    db: AsyncSession, option_id: UUID, label: str
) -> Optional[ProjectOption]:
    obj = await get_project_option(db, option_id)
    if not obj:
        return None
    obj.label = label
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def set_default_project_option(
    db: AsyncSession, option_id: UUID
) -> Optional[ProjectOption]:
    obj = await get_project_option(db, option_id)
    if not obj:
        return None

    q = select(ProjectOption).where(
        ProjectOption.stage_instance_id == obj.stage_instance_id,
        ProjectOption.report_number == obj.report_number,
        ProjectOption.is_default == True,
    )
    for existing_default in (await db.execute(q)).scalars().all():
        existing_default.is_default = False
        db.add(existing_default)

    obj.is_default = True
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project_option(db: AsyncSession, option_id: UUID) -> bool:
    obj = await get_project_option(db, option_id)
    if not obj:
        return False
    if obj.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the base case option. Set another option as base case first.",
        )
    q = select(ActivityData).where(ActivityData.project_option_id == option_id)
    for ad_row in (await db.execute(q)).scalars().all():
        await db.delete(ad_row)
    await db.flush()
    await db.delete(obj)
    await db.flush()
    return True


# ---------------------------------------------------------------------------
# Emissions total helper
# ---------------------------------------------------------------------------

# Keys whose emissions are read from extra_fields["total_emissions_tco2e"].
# Includes both small-project and large-project table keys.
async def get_total_emissions_for_option(
    db: AsyncSession,
    option_id: UUID,
) -> Decimal:
    """
    Sum reportable actual values from the emissions result ledger. Input JSON is
    used only to identify repeated large-road parameter groups.
    """
    result = await db.execute(
        select(ActivityData.ui_table_key, ActivityData.extra_fields, EmissionsResult.value)
        .join(EmissionsResult, EmissionsResult.activity_data_id == ActivityData.id)
        .where(
            ActivityData.project_option_id == option_id,
            EmissionsResult.is_supplementary.is_(False),
            EmissionsResult.reporting_measure == "actual",
            EmissionsResult.accounting_basis.in_(["common", "location"]),
        )
    )
    total = Decimal(0)
    large_road_groups: dict[tuple, Decimal] = {}
    for table_key, extra, raw_value in result.all():
        value = Decimal(str(raw_value or 0))
        if table_key == "largeRoadParams":
            fields = extra or {}
            group = tuple(fields.get(k) for k in ("gradient", "curvature", "roughness", "ev_uptake_scenario"))
            large_road_groups[group] = max(large_road_groups.get(group, value), value)
        else:
            total += value
    total += sum(large_road_groups.values(), Decimal(0))
    return round(total, 6)


async def set_report_options_status(
    db: AsyncSession,
    stage_instance_id: UUID,
    report_number: int,
    new_status: str,
    justification: Optional[str] = None,
) -> List[ProjectOption]:
    q = select(ProjectOption).where(
        ProjectOption.stage_instance_id == stage_instance_id,
        ProjectOption.report_number == report_number,
    )
    options = (await db.execute(q)).scalars().all()
    for opt in options:
        opt.approval_status = new_status
        if justification is not None:
            opt.current_justification = justification
        elif new_status == "draft":
            opt.current_justification = None
        db.add(opt)
    await db.flush()
    for opt in options:
        await db.refresh(opt)
    return list(options)
