from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.materials import Material
from schemas.materials import MaterialCreate, MaterialUpdate


async def create_material(db: AsyncSession, payload: MaterialCreate) -> Material:
    obj = Material(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_material(db: AsyncSession, material_id: UUID) -> Optional[Material]:
    result = await db.execute(select(Material).where(Material.id == material_id))
    return result.scalars().first()


async def get_material_by_name(db: AsyncSession, name: str) -> Optional[Material]:
    result = await db.execute(select(Material).where(Material.name == name))
    return result.scalars().first()


async def list_materials(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[Material]:
    q = select(Material).order_by(Material.name)
    if is_active is not None:
        q = q.where(Material.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_material(db: AsyncSession, obj: Material, payload: MaterialUpdate) -> Material:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_material(db: AsyncSession, material_id: UUID) -> bool:
    obj = await get_material(db, material_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
