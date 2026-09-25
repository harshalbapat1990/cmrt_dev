from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.vehicle_classes import VehicleClass
from models.vehicle_energy_conversion_rates import VehicleEnergyConversionRate
from schemas.vehicle_energy_conversion_rates import (
    VehicleEnergyConversionRateCreate,
    VehicleEnergyConversionRateOut,
    VehicleEnergyConversionRateUpdate,
)


async def list_vehicle_energy_conversion_rates(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> List[VehicleEnergyConversionRateOut]:
    query = select(VehicleEnergyConversionRate, VehicleClass.name.label("vc_name")).join(
        VehicleClass, VehicleEnergyConversionRate.vehicle_class_id == VehicleClass.id
    )
    if dataset_revision_id is None:
        query = query.where(VehicleEnergyConversionRate.dataset_revision_id.is_(None))
    else:
        query = query.where(VehicleEnergyConversionRate.dataset_revision_id == dataset_revision_id)
    result = await db.execute(query.order_by(VehicleClass.sort_order, VehicleClass.name))
    rows = result.all()
    return [
        VehicleEnergyConversionRateOut(
            id=r.VehicleEnergyConversionRate.id,
            dataset_revision_id=r.VehicleEnergyConversionRate.dataset_revision_id,
            vehicle_class_id=r.VehicleEnergyConversionRate.vehicle_class_id,
            ev_projection_category=r.VehicleEnergyConversionRate.ev_projection_category,
            primary_ice_fuel=r.VehicleEnergyConversionRate.primary_ice_fuel,
            hybrid_fuel_savings_pct=r.VehicleEnergyConversionRate.hybrid_fuel_savings_pct,
            phev_fuel_savings_pct=r.VehicleEnergyConversionRate.phev_fuel_savings_pct,
            bev_energy_shift_kwh_per_l=r.VehicleEnergyConversionRate.bev_energy_shift_kwh_per_l,
            fcev_hydrogen_consumption_kwh_per_l=r.VehicleEnergyConversionRate.fcev_hydrogen_consumption_kwh_per_l,
            source_comments=r.VehicleEnergyConversionRate.source_comments,
            vehicle_class_name=r.vc_name,
        )
        for r in rows
    ]


async def get_vehicle_energy_conversion_rate(
    db: AsyncSession, rate_id: UUID
) -> Optional[VehicleEnergyConversionRate]:
    result = await db.execute(
        select(VehicleEnergyConversionRate).where(VehicleEnergyConversionRate.id == rate_id)
    )
    return result.scalars().first()


async def get_vehicle_energy_conversion_rate_by_class(
    db: AsyncSession,
    vehicle_class_id: UUID,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[VehicleEnergyConversionRate]:
    query = select(VehicleEnergyConversionRate).where(
        VehicleEnergyConversionRate.vehicle_class_id == vehicle_class_id
    )
    if dataset_revision_id is None:
        query = query.where(VehicleEnergyConversionRate.dataset_revision_id.is_(None))
    else:
        query = query.where(VehicleEnergyConversionRate.dataset_revision_id == dataset_revision_id)
    result = await db.execute(query)
    return result.scalars().first()


async def create_vehicle_energy_conversion_rate(
    db: AsyncSession, payload: VehicleEnergyConversionRateCreate
) -> VehicleEnergyConversionRate:
    obj = VehicleEnergyConversionRate(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_vehicle_energy_conversion_rate(
    db: AsyncSession,
    obj: VehicleEnergyConversionRate,
    payload: VehicleEnergyConversionRateUpdate,
) -> VehicleEnergyConversionRate:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_vehicle_energy_conversion_rate(
    db: AsyncSession, obj: VehicleEnergyConversionRate
) -> None:
    await db.delete(obj)
    await db.flush()
