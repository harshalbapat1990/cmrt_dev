from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.vehicle_classes import VehicleClass
from models.interrupted_vehicles import InterruptedVehicle
from schemas.interrupted_vehicles import (
    InterruptedVehicleCreate,
    InterruptedVehicleOut,
    InterruptedVehicleUpdate,
)


async def list_interrupted_vehicles(db: AsyncSession) -> List[InterruptedVehicleOut]:
    result = await db.execute(
        select(InterruptedVehicle, VehicleClass.name.label("vc_name"))
        .join(VehicleClass, InterruptedVehicle.vehicle_class_id == VehicleClass.id)
        .order_by(VehicleClass.sort_order, VehicleClass.name)
    )
    rows = result.all()
    return [
        InterruptedVehicleOut(
            id=r.InterruptedVehicle.id,
            dataset_revision_id=r.InterruptedVehicle.dataset_revision_id,
            vehicle_class_id=r.InterruptedVehicle.vehicle_class_id,
            coefficient_a=r.InterruptedVehicle.coefficient_a,
            coefficient_b=r.InterruptedVehicle.coefficient_b,
            vehicle_class_name=r.vc_name,
        )
        for r in rows
    ]


async def get_interrupted_vehicle(
    db: AsyncSession, interrupted_vehicle_id: UUID
) -> Optional[InterruptedVehicle]:
    result = await db.execute(
        select(InterruptedVehicle).where(InterruptedVehicle.id == interrupted_vehicle_id)
    )
    return result.scalars().first()


async def get_interrupted_vehicle_by_class(
    db: AsyncSession,
    vehicle_class_id: UUID,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[InterruptedVehicle]:
    query = select(InterruptedVehicle).where(InterruptedVehicle.vehicle_class_id == vehicle_class_id)
    if dataset_revision_id is None:
        query = query.where(InterruptedVehicle.dataset_revision_id.is_(None))
    else:
        query = query.where(InterruptedVehicle.dataset_revision_id == dataset_revision_id)
    result = await db.execute(query)
    return result.scalars().first()


async def create_interrupted_vehicle(
    db: AsyncSession, payload: InterruptedVehicleCreate
) -> InterruptedVehicle:
    obj = InterruptedVehicle(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_interrupted_vehicle(
    db: AsyncSession, obj: InterruptedVehicle, payload: InterruptedVehicleUpdate
) -> InterruptedVehicle:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_interrupted_vehicle(db: AsyncSession, obj: InterruptedVehicle) -> None:
    await db.delete(obj)
    await db.flush()
