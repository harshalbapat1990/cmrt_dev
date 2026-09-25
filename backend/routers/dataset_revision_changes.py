from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.dataset_revision_changes import DatasetRevisionChangeCreate, DatasetRevisionChangeOut
from crud.dataset_revision_changes import (
    create_dataset_revision_change,
    get_dataset_revision_change,
    list_changes_by_revision,
)

router = APIRouter(prefix="/api/dataset-revision-changes", tags=["dataset-revision-changes"])


@router.post("", response_model=DatasetRevisionChangeOut, status_code=status.HTTP_201_CREATED)
async def create_new_dataset_revision_change(payload: DatasetRevisionChangeCreate, db: AsyncSession = Depends(get_session)):
    obj = await create_dataset_revision_change(db, payload)
    await db.commit()
    return obj


@router.get("/{change_id}", response_model=DatasetRevisionChangeOut)
async def get_dataset_revision_change_by_id(change_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_dataset_revision_change(db, change_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision change not found"
        )
    return obj


@router.get("/by-revision/{revision_id}", response_model=List[DatasetRevisionChangeOut])
async def get_changes_by_revision(revision_id: UUID, db: AsyncSession = Depends(get_session)):
    return await list_changes_by_revision(db, revision_id)
