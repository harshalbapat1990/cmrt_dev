from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.default_wastage_rate import DefaultWastageRate
from schemas.default_wastage_rate import DefaultWastageRateCreate, DefaultWastageRateUpdate


async def create_wastage_rate(db: AsyncSession, payload: DefaultWastageRateCreate) -> DefaultWastageRate:
    obj = DefaultWastageRate(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_wastage_rate(db: AsyncSession, wastage_rate_id: UUID) -> Optional[DefaultWastageRate]:
    result = await db.execute(select(DefaultWastageRate).where(DefaultWastageRate.id == wastage_rate_id))
    return result.scalars().first()


async def list_wastage_rates(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DefaultWastageRate]:
    q = select(DefaultWastageRate)
    if jurisdiction_id is not None:
        q = q.where(DefaultWastageRate.jurisdiction_id == jurisdiction_id)
    if material_id is not None:
        q = q.where(DefaultWastageRate.material_id == material_id)
    if dataset_revision_id is not None:
        q = q.where(DefaultWastageRate.dataset_revision_id == dataset_revision_id)
    result = await db.execute(
        q.order_by(DefaultWastageRate.jurisdiction_id, DefaultWastageRate.material_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_wastage_rate(
    db: AsyncSession, obj: DefaultWastageRate, payload: DefaultWastageRateUpdate
) -> DefaultWastageRate:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_wastage_rate(db: AsyncSession, wastage_rate_id: UUID) -> bool:
    obj = await get_wastage_rate(db, wastage_rate_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
