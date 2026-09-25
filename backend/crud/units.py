from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.units import Unit
from schemas.units import UnitCreate, UnitUpdate


async def create_unit(db: AsyncSession, payload: UnitCreate) -> Unit:
    obj = Unit(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_unit(db: AsyncSession, unit_id: UUID) -> Optional[Unit]:
    result = await db.execute(select(Unit).where(Unit.id == unit_id))
    return result.scalars().first()


async def get_unit_by_code(db: AsyncSession, code: str) -> Optional[Unit]:
    result = await db.execute(select(Unit).where(Unit.code == code))
    return result.scalars().first()


async def list_units(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Unit]:
    result = await db.execute(select(Unit).order_by(Unit.code).offset(skip).limit(limit))
    return result.scalars().all()


async def update_unit(db: AsyncSession, obj: Unit, payload: UnitUpdate) -> Unit:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_unit(db: AsyncSession, unit_id: UUID) -> bool:
    obj = await get_unit(db, unit_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
