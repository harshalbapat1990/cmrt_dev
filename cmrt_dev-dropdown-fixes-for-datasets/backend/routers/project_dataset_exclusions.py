from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.project_dataset_exclusions import (
    ProjectDatasetExclusionCreate,
    ProjectDatasetExclusionOut,
    ProjectDatasetExclusionUpdate,
)
from crud.project_dataset_exclusions import (
    create_project_dataset_exclusion,
    get_project_dataset_exclusion,
    list_exclusions_by_project,
    update_project_dataset_exclusion,
    delete_project_dataset_exclusion,
)

router = APIRouter(prefix="/api/project-dataset-exclusions", tags=["project-dataset-exclusions"])


@router.post("", response_model=ProjectDatasetExclusionOut, status_code=status.HTTP_201_CREATED)
async def create_new_project_dataset_exclusion(payload: ProjectDatasetExclusionCreate, db: AsyncSession = Depends(get_session)):
    obj = await create_project_dataset_exclusion(db, payload)
    await db.commit()
    return obj


@router.get("/by-project/{project_id}", response_model=List[ProjectDatasetExclusionOut])
async def get_exclusions_by_project(project_id: UUID, db: AsyncSession = Depends(get_session)):
    return await list_exclusions_by_project(db, project_id)


@router.get("/{exclusion_id}", response_model=ProjectDatasetExclusionOut)
async def get_project_dataset_exclusion_by_id(exclusion_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_project_dataset_exclusion(db, exclusion_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset exclusion not found"
        )
    return obj


@router.patch("/{exclusion_id}", response_model=ProjectDatasetExclusionOut)
async def patch_project_dataset_exclusion(exclusion_id: UUID, payload: ProjectDatasetExclusionUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_project_dataset_exclusion(db, exclusion_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset exclusion not found"
        )
    obj = await update_project_dataset_exclusion(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{exclusion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_dataset_exclusion(exclusion_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_project_dataset_exclusion(db, exclusion_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset exclusion not found"
        )
    await db.commit()
    return None
