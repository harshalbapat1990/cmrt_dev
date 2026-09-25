from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.waste_treatments import WasteTreatment
from schemas.waste_treatments import WasteTreatmentCreate, WasteTreatmentUpdate


async def create_waste_treatment(db: AsyncSession, payload: WasteTreatmentCreate) -> WasteTreatment:
    obj = WasteTreatment(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_waste_treatment(db: AsyncSession, waste_treatment_id: UUID) -> Optional[WasteTreatment]:
    result = await db.execute(select(WasteTreatment).where(WasteTreatment.id == waste_treatment_id))
    return result.scalars().first()


async def get_waste_treatment_by_name(db: AsyncSession, name: str) -> Optional[WasteTreatment]:
    result = await db.execute(select(WasteTreatment).where(WasteTreatment.name == name))
    return result.scalars().first()


async def list_waste_treatments(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[WasteTreatment]:
    q = select(WasteTreatment).order_by(WasteTreatment.name)
    if is_active is not None:
        q = q.where(WasteTreatment.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_waste_treatment(
    db: AsyncSession, obj: WasteTreatment, payload: WasteTreatmentUpdate
) -> WasteTreatment:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_waste_treatment(db: AsyncSession, waste_treatment_id: UUID) -> bool:
    obj = await get_waste_treatment(db, waste_treatment_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
