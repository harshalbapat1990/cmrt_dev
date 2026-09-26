from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.unit_conversions import UnitConversionCreate, UnitConversionOut, UnitConversionUpdate
from crud.unit_conversions import (
    create_unit_conversion,
    get_unit_conversion,
    get_unit_conversion_by_pair,
    list_unit_conversions,
    update_unit_conversion,
    delete_unit_conversion,
)

router = APIRouter(prefix="/api/unit-conversions", tags=["unit-conversions"])


@router.post("", response_model=UnitConversionOut, status_code=status.HTTP_201_CREATED)
async def create_new_unit_conversion(
    payload: UnitConversionCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="unit_conversions",
    )
    existing = await get_unit_conversion_by_pair(
        db, payload.from_unit_id, payload.to_unit_id, payload.dataset_revision_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversion factor for this unit pair already exists",
        )
    obj = await create_unit_conversion(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[UnitConversionOut])
async def get_unit_conversions(
    from_unit_id: Optional[UUID] = None,
    dataset_revision_id: Optional[UUID] = None,
    global_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_unit_conversions(db, from_unit_id, dataset_revision_id, skip, limit, global_only)


@router.get("/{conversion_id}", response_model=UnitConversionOut)
async def get_unit_conversion_by_id(conversion_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_unit_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit conversion not found",
        )
    return obj


@router.patch("/{conversion_id}", response_model=UnitConversionOut)
async def patch_unit_conversion(
    conversion_id: UUID,
    payload: UnitConversionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_unit_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit conversion not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=getattr(obj, "dataset_revision_id", None),
        dataset_type="unit_conversions",
    )
    new_from_unit_id = payload.from_unit_id or obj.from_unit_id
    new_to_unit_id = payload.to_unit_id or obj.to_unit_id
    new_revision_id = (
        payload.dataset_revision_id
        if payload.dataset_revision_id is not None
        else getattr(obj, "dataset_revision_id", None)
    )

    if (
        payload.from_unit_id
        or payload.to_unit_id
        or payload.dataset_revision_id is not None
    ):
        existing = await get_unit_conversion_by_pair(
            db, new_from_unit_id, new_to_unit_id, new_revision_id
        )
        if existing and existing.id != conversion_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversion factor for this unit pair already exists",
            )
    obj = await update_unit_conversion(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{conversion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_unit_conversion(
    conversion_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_unit_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit conversion not found",
        )

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=getattr(obj, "dataset_revision_id", None),
        dataset_type="unit_conversions",
    )

    ok = await delete_unit_conversion(db, conversion_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit conversion not found",
        )

    await db.commit()
    return None
