from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.project_dataset_exclusions import ProjectDatasetExclusion
from schemas.project_dataset_exclusions import (
    ProjectDatasetExclusionCreate,
    ProjectDatasetExclusionUpdate,
)


async def create_project_dataset_exclusion(
    db: AsyncSession, payload: ProjectDatasetExclusionCreate
) -> ProjectDatasetExclusion:
    obj = ProjectDatasetExclusion(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_project_dataset_exclusion(
    db: AsyncSession, exclusion_id: UUID
) -> Optional[ProjectDatasetExclusion]:
    result = await db.execute(
        select(ProjectDatasetExclusion).where(ProjectDatasetExclusion.id == exclusion_id)
    )
    return result.scalars().first()


async def list_exclusions_by_project(
    db: AsyncSession, project_id: UUID
) -> List[ProjectDatasetExclusion]:
    result = await db.execute(
        select(ProjectDatasetExclusion)
        .where(ProjectDatasetExclusion.project_id == project_id)
        .order_by(ProjectDatasetExclusion.created_at)
    )
    return result.scalars().all()


async def update_project_dataset_exclusion(
    db: AsyncSession, obj: ProjectDatasetExclusion, payload: ProjectDatasetExclusionUpdate
) -> ProjectDatasetExclusion:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project_dataset_exclusion(db: AsyncSession, exclusion_id: UUID) -> bool:
    obj = await get_project_dataset_exclusion(db, exclusion_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
