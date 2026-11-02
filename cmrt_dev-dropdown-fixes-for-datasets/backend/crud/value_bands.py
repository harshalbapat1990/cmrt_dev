from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.value_bands import ValueBand
from schemas.value_bands import ValueBandCreate, ValueBandUpdate


async def create_value_band(db: AsyncSession, payload: ValueBandCreate) -> ValueBand:
    obj = ValueBand(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_value_band(db: AsyncSession, code: str) -> Optional[ValueBand]:
    result = await db.execute(select(ValueBand).where(ValueBand.code == code))
    return result.scalars().first()


async def list_value_bands(db: AsyncSession) -> List[ValueBand]:
    result = await db.execute(select(ValueBand).order_by(ValueBand.sort_order, ValueBand.code))
    return result.scalars().all()


async def update_value_band(
    db: AsyncSession, obj: ValueBand, payload: ValueBandUpdate
) -> ValueBand:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_value_band(db: AsyncSession, code: str) -> bool:
    obj = await get_value_band(db, code)
    if not obj:
        return False
    await db.delete(obj)
    return True
