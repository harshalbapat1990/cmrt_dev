from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.project_dataset_revisions import ProjectDatasetRevision
from models.dataset_revisions import DatasetRevision
from schemas.project_dataset_revisions import (
    ProjectDatasetRevisionCreate,
    ProjectDatasetRevisionUpdate,
)


async def create_project_dataset_revision(
    db: AsyncSession, payload: ProjectDatasetRevisionCreate
) -> ProjectDatasetRevision:
    obj = ProjectDatasetRevision(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def upsert_project_dataset_revision(
    db: AsyncSession, payload: ProjectDatasetRevisionCreate
) -> ProjectDatasetRevision:
    result = await db.execute(
        select(ProjectDatasetRevision).where(
            ProjectDatasetRevision.project_id == payload.project_id,
        )
    )
    existing_list = result.scalars().all()

    for existing in existing_list:
        await db.delete(existing)
    if existing_list:
        await db.flush()

    obj = ProjectDatasetRevision(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_project_dataset_revision(
    db: AsyncSession, pdr_id: UUID
) -> Optional[ProjectDatasetRevision]:
    result = await db.execute(
        select(ProjectDatasetRevision).where(ProjectDatasetRevision.id == pdr_id)
    )
    return result.scalars().first()


async def list_project_dataset_revisions_by_project(
    db: AsyncSession, project_id: UUID
) -> List[ProjectDatasetRevision]:
    result = await db.execute(
        select(ProjectDatasetRevision)
        .where(ProjectDatasetRevision.project_id == project_id)
        .order_by(ProjectDatasetRevision.applied_at.desc())
    )
    return list(result.scalars().all())


async def update_project_dataset_revision(
    db: AsyncSession, obj: ProjectDatasetRevision, payload: ProjectDatasetRevisionUpdate
) -> ProjectDatasetRevision:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project_dataset_revision(db: AsyncSession, pdr_id: UUID) -> bool:
    obj = await get_project_dataset_revision(db, pdr_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    """Return the status string of a DatasetRevision or None if not found."""
    result = await db.execute(
        select(DatasetRevision.status).where(DatasetRevision.id == revision_id)
    )
    row = result.first()
    return row[0] if row else None

