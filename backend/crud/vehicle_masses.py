from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.vehicle_classes import VehicleClass
from models.vehicle_masses import VehicleMass
from schemas.vehicle_masses import VehicleMassCreate, VehicleMassOut, VehicleMassUpdate


async def list_vehicle_masses(db: AsyncSession) -> List[VehicleMassOut]:
    result = await db.execute(
        select(VehicleMass, VehicleClass.name.label("vc_name"))
        .join(VehicleClass, VehicleMass.vehicle_class_id == VehicleClass.id)
        .order_by(VehicleClass.sort_order, VehicleClass.name)
    )
    rows = result.all()
    return [
        VehicleMassOut(
            id=r.VehicleMass.id,
            vehicle_class_id=r.VehicleMass.vehicle_class_id,
            reference_gcm_tonnes=r.VehicleMass.reference_gcm_tonnes,
            max_payload_tonnes=r.VehicleMass.max_payload_tonnes,
            gvm_tonnes=r.VehicleMass.gvm_tonnes,
            assumed_payload_pct=r.VehicleMass.assumed_payload_pct,
            vehicle_class_name=r.vc_name,
        )
        for r in rows
    ]


async def get_vehicle_mass(db: AsyncSession, vehicle_mass_id: UUID) -> Optional[VehicleMass]:
    result = await db.execute(select(VehicleMass).where(VehicleMass.id == vehicle_mass_id))
    return result.scalars().first()


async def get_vehicle_mass_by_class(
    db: AsyncSession, vehicle_class_id: UUID
) -> Optional[VehicleMass]:
    result = await db.execute(
        select(VehicleMass).where(VehicleMass.vehicle_class_id == vehicle_class_id)
    )
    return result.scalars().first()


async def create_vehicle_mass(db: AsyncSession, payload: VehicleMassCreate) -> VehicleMass:
    obj = VehicleMass(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_vehicle_mass(
    db: AsyncSession, obj: VehicleMass, payload: VehicleMassUpdate
) -> VehicleMass:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_vehicle_mass(db: AsyncSession, obj: VehicleMass) -> None:
    await db.delete(obj)
    await db.flush()
