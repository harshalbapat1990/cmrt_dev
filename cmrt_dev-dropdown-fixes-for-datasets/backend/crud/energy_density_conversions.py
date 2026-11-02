from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.energy_density_conversions import EnergyDensityConversion
from schemas.energy_density_conversions import EnergyDensityConversionCreate, EnergyDensityConversionUpdate


async def create_energy_density_conversion(
    db: AsyncSession, payload: EnergyDensityConversionCreate
) -> EnergyDensityConversion:
    obj = EnergyDensityConversion(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_energy_density_conversion(db: AsyncSession, conversion_id: UUID) -> Optional[EnergyDensityConversion]:
    result = await db.execute(select(EnergyDensityConversion).where(EnergyDensityConversion.id == conversion_id))
    return result.scalars().first()


async def list_energy_density_conversions(
    db: AsyncSession,
    category: Optional[str] = None,
    unit_id: Optional[UUID] = None,
    search: Optional[str] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[EnergyDensityConversion]:
    q = select(EnergyDensityConversion)
    if category is not None:
        q = q.where(EnergyDensityConversion.category == category)
    if unit_id is not None:
        q = q.where(EnergyDensityConversion.unit_id == unit_id)
    if search is not None:
        like = f"%{search}%"
        q = q.where(
            EnergyDensityConversion.name.ilike(like)
            | EnergyDensityConversion.source.ilike(like)
        )
    if dataset_revision_id is not None:
        q = q.where(EnergyDensityConversion.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q.order_by(EnergyDensityConversion.category, EnergyDensityConversion.name).offset(skip).limit(limit))
    return result.scalars().all()


async def update_energy_density_conversion(
    db: AsyncSession, obj: EnergyDensityConversion, payload: EnergyDensityConversionUpdate
) -> EnergyDensityConversion:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_energy_density_conversion(db: AsyncSession, conversion_id: UUID) -> bool:
    obj = await get_energy_density_conversion(db, conversion_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
