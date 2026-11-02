from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.recycled_content_factors import RecycledContentFactor
from schemas.recycled_content_factors import (
    RecycledContentFactorCreate,
    RecycledContentFactorUpdate,
)


async def get_recycled_content_factor(
    db: AsyncSession,
    record_id: UUID,
) -> Optional[RecycledContentFactor]:
    result = await db.execute(
        select(RecycledContentFactor).where(RecycledContentFactor.id == record_id)
    )
    return result.scalars().first()


async def get_by_jurisdiction_and_source(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID],
    emissions_source: str,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[RecycledContentFactor]:
    q = select(RecycledContentFactor).where(
        RecycledContentFactor.emissions_source == emissions_source,
        RecycledContentFactor.is_active.is_(True),
    )
    if jurisdiction_id is None:
        q = q.where(RecycledContentFactor.jurisdiction_id.is_(None))
    else:
        q = q.where(RecycledContentFactor.jurisdiction_id == jurisdiction_id)
    if dataset_revision_id is None:
        q = q.where(RecycledContentFactor.dataset_revision_id.is_(None))
    else:
        q = q.where(RecycledContentFactor.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q)
    return result.scalars().first()


async def list_recycled_content_factors(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    emissions_sub_category_id: Optional[UUID] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[RecycledContentFactor]:
    q = (
        select(RecycledContentFactor)
        .where(RecycledContentFactor.is_active.is_(True))
        .order_by(RecycledContentFactor.emissions_source)
    )
    if jurisdiction_id is not None:
        q = q.where(RecycledContentFactor.jurisdiction_id == jurisdiction_id)
    if emissions_sub_category_id is not None:
        q = q.where(
            RecycledContentFactor.emissions_sub_category_id == emissions_sub_category_id
        )
    if dataset_revision_id is None:
        q = q.where(RecycledContentFactor.dataset_revision_id.is_(None))
    else:
        q = q.where(RecycledContentFactor.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_recycled_content_factor(
    db: AsyncSession,
    payload: RecycledContentFactorCreate,
) -> RecycledContentFactor:
    obj = RecycledContentFactor(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_recycled_content_factor(
    db: AsyncSession,
    obj: RecycledContentFactor,
    payload: RecycledContentFactorUpdate,
) -> RecycledContentFactor:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_recycled_content_factor(
    db: AsyncSession,
    record_id: UUID,
) -> bool:
    obj = await get_recycled_content_factor(db, record_id)
    if obj is None:
        return False
    obj.is_active = False
    db.add(obj)
    await db.flush()
    return True


async def upsert_recycled_content_factor(
    db: AsyncSession,
    payload: RecycledContentFactorCreate,
) -> tuple[RecycledContentFactor, bool]:
    """
    Insert or update an active row keyed by jurisdiction + emissions_source + revision.
    Returns (record, created) where created is True for a new row.
    """
    existing = await get_by_jurisdiction_and_source(
        db,
        jurisdiction_id=payload.jurisdiction_id,
        emissions_source=payload.emissions_source,
        dataset_revision_id=payload.dataset_revision_id,
    )
    if existing:
        update_payload = RecycledContentFactorUpdate(
            emissions_sub_category_id=payload.emissions_sub_category_id,
            recycled_content_pct=payload.recycled_content_pct,
            reused_content_pct=payload.reused_content_pct,
            notes=payload.notes,
        )
        updated = await update_recycled_content_factor(db, existing, update_payload)
        return updated, False
    created = await create_recycled_content_factor(db, payload)
    return created, True