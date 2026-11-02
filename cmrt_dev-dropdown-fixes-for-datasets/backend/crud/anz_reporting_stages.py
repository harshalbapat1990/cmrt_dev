from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.anz_reporting_stages import AnzReportingStage
from schemas.anz_reporting_stages import AnzReportingStageCreate, AnzReportingStageUpdate


async def create_anz_reporting_stage(db: AsyncSession, payload: AnzReportingStageCreate) -> AnzReportingStage:
    obj = AnzReportingStage(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_anz_reporting_stage(db: AsyncSession, stage_id: UUID) -> Optional[AnzReportingStage]:
    result = await db.execute(select(AnzReportingStage).where(AnzReportingStage.id == stage_id))
    return result.scalars().first()


async def get_anz_reporting_stage_by_name(db: AsyncSession, name: str) -> Optional[AnzReportingStage]:
    result = await db.execute(select(AnzReportingStage).where(AnzReportingStage.name == name))
    return result.scalars().first()


async def list_anz_reporting_stages(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AnzReportingStage]:
    result = await db.execute(
        select(AnzReportingStage).order_by(AnzReportingStage.sequence).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def update_anz_reporting_stage(
    db: AsyncSession, obj: AnzReportingStage, payload: AnzReportingStageUpdate
) -> AnzReportingStage:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_anz_reporting_stage(db: AsyncSession, stage_id: UUID) -> bool:
    obj = await get_anz_reporting_stage(db, stage_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
