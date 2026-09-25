from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.metric_types import MetricType
from schemas.metric_types import MetricTypeCreate, MetricTypeUpdate


async def create_metric_type(db: AsyncSession, payload: MetricTypeCreate) -> MetricType:
    obj = MetricType(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_metric_type(db: AsyncSession, metric_type_id: UUID) -> Optional[MetricType]:
    result = await db.execute(select(MetricType).where(MetricType.id == metric_type_id))
    return result.scalars().first()


async def get_metric_type_by_code(db: AsyncSession, code: str) -> Optional[MetricType]:
    result = await db.execute(select(MetricType).where(MetricType.code == code))
    return result.scalars().first()


async def list_metric_types(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[MetricType]:
    result = await db.execute(
        select(MetricType).order_by(MetricType.code).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def update_metric_type(
    db: AsyncSession, obj: MetricType, payload: MetricTypeUpdate
) -> MetricType:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_metric_type(db: AsyncSession, metric_type_id: UUID) -> bool:
    obj = await get_metric_type(db, metric_type_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
