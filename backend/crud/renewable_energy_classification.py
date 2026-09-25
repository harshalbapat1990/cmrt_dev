from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.renewable_energy_classification import RenewableEnergyClassification
from schemas.renewable_energy_classification import (
    RenewableEnergyClassificationCreate,
    RenewableEnergyClassificationUpdate,
)


async def get_renewable_energy_classification(
    db: AsyncSession,
    record_id: UUID,
) -> Optional[RenewableEnergyClassification]:
    result = await db.execute(
        select(RenewableEnergyClassification).where(
            RenewableEnergyClassification.id == record_id
        )
    )
    return result.scalars().first()


async def get_by_source(
    db: AsyncSession,
    emissions_source: str,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[RenewableEnergyClassification]:
    q = select(RenewableEnergyClassification).where(
        RenewableEnergyClassification.emissions_source == emissions_source,
        RenewableEnergyClassification.is_active.is_(True),
    )
    if dataset_revision_id is None:
        q = q.where(RenewableEnergyClassification.dataset_revision_id.is_(None))
    else:
        q = q.where(
            RenewableEnergyClassification.dataset_revision_id == dataset_revision_id
        )
    result = await db.execute(q)
    return result.scalars().first()


async def list_renewable_energy_classifications(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[RenewableEnergyClassification]:
    q = (
        select(RenewableEnergyClassification)
        .where(RenewableEnergyClassification.is_active.is_(True))
        .order_by(RenewableEnergyClassification.emissions_source)
    )
    if dataset_revision_id is None:
        q = q.where(RenewableEnergyClassification.dataset_revision_id.is_(None))
    else:
        q = q.where(
            RenewableEnergyClassification.dataset_revision_id == dataset_revision_id
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_renewable_energy_classification(
    db: AsyncSession,
    payload: RenewableEnergyClassificationCreate,
) -> RenewableEnergyClassification:
    obj = RenewableEnergyClassification(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_renewable_energy_classification(
    db: AsyncSession,
    obj: RenewableEnergyClassification,
    payload: RenewableEnergyClassificationUpdate,
) -> RenewableEnergyClassification:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_renewable_energy_classification(
    db: AsyncSession,
    record_id: UUID,
) -> bool:
    obj = await get_renewable_energy_classification(db, record_id)
    if obj is None:
        return False
    obj.is_active = False
    db.add(obj)
    await db.flush()
    return True
