from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.fugitives import FugitiveCreate, FugitiveOut, FugitiveUpdate
from crud.fugitives import (
    create_fugitive,
    get_fugitive,
    list_fugitives,
    update_fugitive,
    delete_fugitive,
)

router = APIRouter(prefix="/api/fugitives", tags=["fugitives"])


@router.post("", response_model=FugitiveOut, status_code=status.HTTP_201_CREATED)
async def create_new_fugitive(
    payload: FugitiveCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="fugitives",
    )
    obj = await create_fugitive(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[FugitiveOut])
async def get_fugitives(
    jurisdiction_id: Optional[UUID] = None,
    search: Optional[str] = None,
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to fugitives belonging to a specific dataset revision"
    ),
    global_only: bool = Query(
        True, description="When true (default), return only global records (dataset_revision_id IS NULL). Set to false to include revision-specific records."
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_fugitives(db, jurisdiction_id, search, dataset_revision_id, global_only, skip, limit)


@router.get("/{fugitive_id}", response_model=FugitiveOut)
async def get_fugitive_by_id(fugitive_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_fugitive(db, fugitive_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fugitive not found")
    return obj


@router.patch("/{fugitive_id}", response_model=FugitiveOut)
async def patch_fugitive(
    fugitive_id: UUID,
    payload: FugitiveUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_fugitive(db, fugitive_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fugitive not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="fugitives",
    )
    obj = await update_fugitive(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{fugitive_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fugitive(
    fugitive_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_fugitive(db, fugitive_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fugitive not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="fugitives",
    )
    ok = await delete_fugitive(db, fugitive_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fugitive not found")
    await db.commit()
    return None
