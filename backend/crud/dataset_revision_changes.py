from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.dataset_revision_changes import DatasetRevisionChange
from schemas.dataset_revision_changes import DatasetRevisionChangeCreate


async def create_dataset_revision_change(
    db: AsyncSession, payload: DatasetRevisionChangeCreate
) -> DatasetRevisionChange:
    obj = DatasetRevisionChange(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_dataset_revision_change(
    db: AsyncSession, change_id: UUID
) -> Optional[DatasetRevisionChange]:
    result = await db.execute(
        select(DatasetRevisionChange).where(DatasetRevisionChange.id == change_id)
    )
    return result.scalars().first()


async def list_changes_by_revision(
    db: AsyncSession, revision_id: UUID, skip: int = 0, limit: int = 500
) -> List[DatasetRevisionChange]:
    result = await db.execute(
        select(DatasetRevisionChange)
        .where(DatasetRevisionChange.dataset_revision_id == revision_id)
        .order_by(DatasetRevisionChange.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
