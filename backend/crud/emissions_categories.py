from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.emissions_categories_new import EmissionsCategoryRecord
from schemas.emissions_categories import EmissionsCategoryCreate, EmissionsCategoryUpdate


async def create_emissions_category(
    db: AsyncSession, payload: EmissionsCategoryCreate
) -> EmissionsCategoryRecord:
    obj = EmissionsCategoryRecord(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_emissions_category(
    db: AsyncSession, category_id: UUID
) -> Optional[EmissionsCategoryRecord]:
    result = await db.execute(
        select(EmissionsCategoryRecord).where(EmissionsCategoryRecord.id == category_id)
    )
    return result.scalars().first()


async def list_emissions_categories(
    db: AsyncSession,
    is_active: Optional[bool] = None,
    scope: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[EmissionsCategoryRecord]:
    query = select(EmissionsCategoryRecord)
    if is_active is not None:
        query = query.where(EmissionsCategoryRecord.is_active == is_active)
    if scope is not None:
        query = query.where(EmissionsCategoryRecord.scope == scope)
    query = query.order_by(EmissionsCategoryRecord.sort_order, EmissionsCategoryRecord.name)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def list_emissions_categories_by_parent(
    db: AsyncSession, parent_category_id: Optional[UUID], skip: int = 0, limit: int = 100
) -> List[EmissionsCategoryRecord]:
    """List categories with a specific parent (pass None to list top-level)."""
    query = select(EmissionsCategoryRecord).where(
        EmissionsCategoryRecord.parent_category_id == parent_category_id
    )
    query = query.order_by(EmissionsCategoryRecord.sort_order, EmissionsCategoryRecord.name)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_emissions_category(
    db: AsyncSession, obj: EmissionsCategoryRecord, payload: EmissionsCategoryUpdate
) -> EmissionsCategoryRecord:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_emissions_category(db: AsyncSession, category_id: UUID) -> bool:
    obj = await get_emissions_category(db, category_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
