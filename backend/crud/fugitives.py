from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.fugitives import Fugitive
from schemas.fugitives import FugitiveCreate, FugitiveUpdate


async def create_fugitive(db: AsyncSession, payload: FugitiveCreate) -> Fugitive:
    obj = Fugitive(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_fugitive(db: AsyncSession, fugitive_id: UUID) -> Optional[Fugitive]:
    result = await db.execute(select(Fugitive).where(Fugitive.id == fugitive_id))
    return result.scalars().first()


async def list_fugitives(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    search: Optional[str] = None,
    dataset_revision_id: Optional[UUID] = None,
    global_only: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> List[Fugitive]:
    q = select(Fugitive)
    if jurisdiction_id is not None:
        q = q.where(Fugitive.jurisdiction_id == jurisdiction_id)
    if search is not None:
        like = f"%{search}%"
        q = q.where(
            Fugitive.equipment_type.ilike(like)
            | Fugitive.source_comments.ilike(like)
        )
    if dataset_revision_id is not None:
        q = q.where(Fugitive.dataset_revision_id == dataset_revision_id)
    elif global_only:
        q = q.where(Fugitive.dataset_revision_id.is_(None))
    result = await db.execute(q.order_by(Fugitive.jurisdiction_id, Fugitive.equipment_type).offset(skip).limit(limit))
    return result.scalars().all()


async def update_fugitive(db: AsyncSession, obj: Fugitive, payload: FugitiveUpdate) -> Fugitive:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_fugitive(db: AsyncSession, fugitive_id: UUID) -> bool:
    obj = await get_fugitive(db, fugitive_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
