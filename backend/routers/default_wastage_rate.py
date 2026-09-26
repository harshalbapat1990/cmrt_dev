from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.default_wastage_rate import DefaultWastageRateCreate, DefaultWastageRateOut, DefaultWastageRateUpdate
from crud.default_wastage_rate import (
    create_wastage_rate,
    get_wastage_rate,
    list_wastage_rates,
    update_wastage_rate,
    delete_wastage_rate,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/wastage-rates", tags=["wastage-rates"])


@router.post("", response_model=DefaultWastageRateOut, status_code=status.HTTP_201_CREATED)
async def create_new_wastage_rate(
    payload: DefaultWastageRateCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="default_wastage_rate",
    )
    obj = await create_wastage_rate(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[DefaultWastageRateOut])
async def get_wastage_rates(
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to wastage rates belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_wastage_rates(db, jurisdiction_id, material_id, dataset_revision_id, skip, limit)


@router.get("/{wastage_rate_id}", response_model=DefaultWastageRateOut)
async def get_wastage_rate_by_id(wastage_rate_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_wastage_rate(db, wastage_rate_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastage rate not found")
    return obj


@router.patch("/{wastage_rate_id}", response_model=DefaultWastageRateOut)
async def patch_wastage_rate(
    wastage_rate_id: UUID,
    payload: DefaultWastageRateUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_wastage_rate(db, wastage_rate_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastage rate not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_wastage_rate",
    )
    obj = await update_wastage_rate(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{wastage_rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wastage_rate(
    wastage_rate_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_wastage_rate(db, wastage_rate_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastage rate not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_wastage_rate",
    )
    ok = await delete_wastage_rate(db, wastage_rate_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wastage rate not found")
    await db.commit()
    return None

protect_dataset_reads(router)
