from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.jurisdiction_reporting_stages import JurisdictionReportingStage
from schemas.jurisdiction_reporting_stages import (
    JurisdictionReportingStageCreate,
    JurisdictionReportingStageUpdate,
)


async def create_jurisdiction_reporting_stage(
    db: AsyncSession, payload: JurisdictionReportingStageCreate
) -> JurisdictionReportingStage:
    obj = JurisdictionReportingStage(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_jurisdiction_reporting_stage(
    db: AsyncSession, stage_id: UUID
) -> Optional[JurisdictionReportingStage]:
    result = await db.execute(
        select(JurisdictionReportingStage).where(JurisdictionReportingStage.id == stage_id)
    )
    return result.scalars().first()


async def list_jurisdiction_reporting_stages(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[JurisdictionReportingStage]:
    result = await db.execute(
        select(JurisdictionReportingStage)
        .order_by(JurisdictionReportingStage.sequence)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def list_jurisdiction_reporting_stages_by_jurisdiction(
    db: AsyncSession, jurisdiction_id: UUID, skip: int = 0, limit: int = 100
) -> List[JurisdictionReportingStage]:
    result = await db.execute(
        select(JurisdictionReportingStage)
        .where(JurisdictionReportingStage.jurisdiction_id == jurisdiction_id)
        .order_by(JurisdictionReportingStage.sequence)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_jurisdiction_reporting_stage(
    db: AsyncSession, obj: JurisdictionReportingStage, payload: JurisdictionReportingStageUpdate
) -> JurisdictionReportingStage:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_jurisdiction_reporting_stage(db: AsyncSession, stage_id: UUID) -> bool:
    obj = await get_jurisdiction_reporting_stage(db, stage_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
