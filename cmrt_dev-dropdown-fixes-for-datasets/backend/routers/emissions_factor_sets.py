from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.emissions_factor_sets import (
    create_emissions_factor_set,
    get_emissions_factor_set,
    update_emissions_factor_set,
    delete_emissions_factor_set,
    count_factor_sets_for_revision,
)
from schemas.emissions_factor_sets import (
    EmissionsFactorSetCreate,
    EmissionsFactorSetUpdate,
    EmissionsFactorSetDuplicate,
    EmissionsFactorSetOut,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/emissions-factor-sets", tags=["emissions-factor-sets"])


async def _assert_editable(db, principal, obj=None, revision_id=None):
    rid = revision_id if revision_id is not None else (obj.dataset_revision_id if obj else None)
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=rid,
        dataset_type="emissions_factor_sets",
    )


@router.post("", response_model=EmissionsFactorSetOut, status_code=status.HTTP_201_CREATED)
async def create_factor_set(
    payload: EmissionsFactorSetCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await _assert_editable(db, principal, revision_id=payload.dataset_revision_id)
    obj = await create_emissions_factor_set(db, payload)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{factor_set_id}", response_model=EmissionsFactorSetOut)
async def get_factor_set(factor_set_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_emissions_factor_set(db, factor_set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Emissions factor set not found")
    return obj


@router.patch("/{factor_set_id}", response_model=EmissionsFactorSetOut)
async def patch_factor_set(
    factor_set_id: UUID,
    payload: EmissionsFactorSetUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_emissions_factor_set(db, factor_set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Emissions factor set not found")
    if obj.is_locked:
        raise HTTPException(status_code=409, detail="Locked emissions factor sets cannot be modified")
    await _assert_editable(db, principal, obj=obj)
    obj = await update_emissions_factor_set(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{factor_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_factor_set(
    factor_set_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_emissions_factor_set(db, factor_set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Emissions factor set not found")
    if obj.is_locked:
        raise HTTPException(status_code=409, detail="Locked emissions factor sets cannot be deleted")
    await _assert_editable(db, principal, obj=obj)
    await delete_emissions_factor_set(db, factor_set_id)
    await db.commit()
    return None


@router.post("/{factor_set_id}/lock", response_model=EmissionsFactorSetOut)
async def lock_factor_set(
    factor_set_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_emissions_factor_set(db, factor_set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Emissions factor set not found")
    await _assert_editable(db, principal, obj=obj)
    obj.is_locked = True
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{factor_set_id}/duplicate", response_model=EmissionsFactorSetOut, status_code=status.HTTP_201_CREATED)
async def duplicate_factor_set(
    factor_set_id: UUID,
    payload: EmissionsFactorSetDuplicate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    source = await get_emissions_factor_set(db, factor_set_id)
    if not source:
        raise HTTPException(status_code=404, detail="Emissions factor set not found")
    await _assert_editable(db, principal, obj=source)
    clone_payload = EmissionsFactorSetCreate(
        name=payload.name or source.name,
        version=payload.new_version,
        dataset_revision_id=source.dataset_revision_id,
        notes=source.notes,
    )
    clone = await create_emissions_factor_set(db, clone_payload)
    clone.is_locked = False
    await db.commit()
    await db.refresh(clone)
    return clone

protect_dataset_reads(router)
