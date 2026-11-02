from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.operational_equipment import OperationalEquipment
from schemas.operational_equipment import OperationalEquipmentCreate, OperationalEquipmentUpdate


async def create_operational_equipment(
    db: AsyncSession, payload: OperationalEquipmentCreate
) -> OperationalEquipment:
    obj = OperationalEquipment(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_operational_equipment(
    db: AsyncSession, record_id: UUID
) -> Optional[OperationalEquipment]:
    result = await db.execute(
        select(OperationalEquipment).where(OperationalEquipment.id == record_id)
    )
    return result.scalars().first()


async def get_operational_equipment_by_item(
    db: AsyncSession,
    item: str,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[OperationalEquipment]:
    q = select(OperationalEquipment).where(
        OperationalEquipment.item == item,
        OperationalEquipment.is_active.is_(True),
    )
    if dataset_revision_id is not None:
        q = q.where(OperationalEquipment.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q)
    return result.scalars().first()


async def list_operational_equipment(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[OperationalEquipment]:
    q = (
        select(OperationalEquipment)
        .where(OperationalEquipment.is_active.is_(True))
        .order_by(OperationalEquipment.group_name, OperationalEquipment.item)
    )
    if dataset_revision_id is not None:
        q = q.where(OperationalEquipment.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def supersede_operational_equipment(
    db: AsyncSession,
    old_obj: OperationalEquipment,
    patch: dict,
) -> OperationalEquipment:
    old_obj.is_active = False
    db.add(old_obj)

    skip_cols = {"id", "is_active"}
    data = {
        c.name: getattr(old_obj, c.name)
        for c in OperationalEquipment.__table__.columns
        if c.name not in skip_cols
    }
    data.update(patch)
    new_obj = OperationalEquipment(**data, is_active=True)
    db.add(new_obj)
    await db.flush()
    await db.refresh(new_obj)
    return new_obj


async def delete_operational_equipment(db: AsyncSession, record_id: UUID) -> bool:
    obj = await get_operational_equipment(db, record_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
