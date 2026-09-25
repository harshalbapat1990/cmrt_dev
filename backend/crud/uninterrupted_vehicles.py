from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.vehicle_classes import VehicleClass
from models.uninterrupted_vehicles import UninterruptedVehicle
from schemas.uninterrupted_vehicles import (
    UninterruptedVehicleCreate,
    UninterruptedVehicleOut,
    UninterruptedVehicleUpdate,
)


async def list_uninterrupted_vehicles(
    db: AsyncSession,
    vehicle_class_id: Optional[UUID] = None,
    gradient_m_per_km: Optional[Decimal] = None,
    curvature_deg_per_km: Optional[Decimal] = None,
    dataset_revision_id: Optional[UUID] = None,
) -> List[UninterruptedVehicleOut]:
    q = (
        select(UninterruptedVehicle, VehicleClass.name.label("vc_name"))
        .join(VehicleClass, UninterruptedVehicle.vehicle_class_id == VehicleClass.id)
    )
    if vehicle_class_id is not None:
        q = q.where(UninterruptedVehicle.vehicle_class_id == vehicle_class_id)
    if gradient_m_per_km is not None:
        q = q.where(UninterruptedVehicle.gradient_m_per_km == gradient_m_per_km)
    if curvature_deg_per_km is not None:
        q = q.where(UninterruptedVehicle.curvature_deg_per_km == curvature_deg_per_km)
    if dataset_revision_id is None:
        q = q.where(UninterruptedVehicle.dataset_revision_id.is_(None))
    else:
        q = q.where(UninterruptedVehicle.dataset_revision_id == dataset_revision_id)
    q = q.order_by(
        VehicleClass.sort_order,
        VehicleClass.name,
        UninterruptedVehicle.gradient_m_per_km,
        UninterruptedVehicle.curvature_deg_per_km,
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        UninterruptedVehicleOut(
            id=r.UninterruptedVehicle.id,
            dataset_revision_id=r.UninterruptedVehicle.dataset_revision_id,
            vehicle_class_id=r.UninterruptedVehicle.vehicle_class_id,
            gradient_m_per_km=r.UninterruptedVehicle.gradient_m_per_km,
            curvature_deg_per_km=r.UninterruptedVehicle.curvature_deg_per_km,
            base_fuel_l_per_100km=r.UninterruptedVehicle.base_fuel_l_per_100km,
            k1=r.UninterruptedVehicle.k1,
            k2=r.UninterruptedVehicle.k2,
            k3=r.UninterruptedVehicle.k3,
            k4=r.UninterruptedVehicle.k4,
            k5=r.UninterruptedVehicle.k5,
            vehicle_class_name=r.vc_name,
        )
        for r in rows
    ]


async def get_uninterrupted_vehicle(
    db: AsyncSession, uninterrupted_vehicle_id: UUID
) -> Optional[UninterruptedVehicle]:
    result = await db.execute(
        select(UninterruptedVehicle).where(UninterruptedVehicle.id == uninterrupted_vehicle_id)
    )
    return result.scalars().first()


async def get_uninterrupted_vehicle_by_unique(
    db: AsyncSession,
    vehicle_class_id: UUID,
    gradient_m_per_km: Decimal,
    curvature_deg_per_km: Decimal,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[UninterruptedVehicle]:
    query = select(UninterruptedVehicle).where(
        UninterruptedVehicle.vehicle_class_id == vehicle_class_id,
        UninterruptedVehicle.gradient_m_per_km == gradient_m_per_km,
        UninterruptedVehicle.curvature_deg_per_km == curvature_deg_per_km,
    )
    if dataset_revision_id is None:
        query = query.where(UninterruptedVehicle.dataset_revision_id.is_(None))
    else:
        query = query.where(UninterruptedVehicle.dataset_revision_id == dataset_revision_id)
    result = await db.execute(query)
    return result.scalars().first()


async def create_uninterrupted_vehicle(
    db: AsyncSession, payload: UninterruptedVehicleCreate
) -> UninterruptedVehicle:
    obj = UninterruptedVehicle(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_uninterrupted_vehicle(
    db: AsyncSession, obj: UninterruptedVehicle, payload: UninterruptedVehicleUpdate
) -> UninterruptedVehicle:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_uninterrupted_vehicle(db: AsyncSession, obj: UninterruptedVehicle) -> None:
    await db.delete(obj)
    await db.flush()
