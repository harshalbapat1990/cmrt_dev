from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.vehicle_classes import VehicleClass
from schemas.vehicle_classes import VehicleClassCreate, VehicleClassOut, VehicleClassUpdate


async def list_vehicle_classes(db: AsyncSession) -> List[VehicleClassOut]:
    result = await db.execute(select(VehicleClass).order_by(VehicleClass.sort_order, VehicleClass.name))
    rows = result.scalars().all()
    return [VehicleClassOut.model_validate(r) for r in rows]


async def get_vehicle_class(db: AsyncSession, vehicle_class_id: UUID) -> Optional[VehicleClass]:
    result = await db.execute(select(VehicleClass).where(VehicleClass.id == vehicle_class_id))
    return result.scalars().first()


async def create_vehicle_class(db: AsyncSession, payload: VehicleClassCreate) -> VehicleClass:
    obj = VehicleClass(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_vehicle_class(
    db: AsyncSession, obj: VehicleClass, payload: VehicleClassUpdate
) -> VehicleClass:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_vehicle_class(db: AsyncSession, obj: VehicleClass) -> None:
    await db.delete(obj)
    await db.flush()
