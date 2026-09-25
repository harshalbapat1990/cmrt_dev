from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.energy_density_conversions import (
    EnergyDensityConversionCreate,
    EnergyDensityConversionOut,
    EnergyDensityConversionUpdate,
)
from crud.energy_density_conversions import (
    create_energy_density_conversion,
    get_energy_density_conversion,
    list_energy_density_conversions,
    update_energy_density_conversion,
    delete_energy_density_conversion,
)

router = APIRouter(prefix="/api/energy-density-conversions", tags=["energy-density-conversions"])


@router.post("", response_model=EnergyDensityConversionOut, status_code=status.HTTP_201_CREATED)
async def create_new_energy_density_conversion(
    payload: EnergyDensityConversionCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="energy_density_conversions",
    )
    obj = await create_energy_density_conversion(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[EnergyDensityConversionOut])
async def get_energy_density_conversions(
    category: Optional[str] = None,
    unit_id: Optional[UUID] = None,
    search: Optional[str] = None,
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to energy density conversions belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_energy_density_conversions(db, category, unit_id, search, dataset_revision_id, skip, limit)


@router.get("/{conversion_id}", response_model=EnergyDensityConversionOut)
async def get_energy_density_conversion_by_id(conversion_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_energy_density_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Energy density conversion not found")
    return obj


@router.patch("/{conversion_id}", response_model=EnergyDensityConversionOut)
async def patch_energy_density_conversion(
    conversion_id: UUID,
    payload: EnergyDensityConversionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_energy_density_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Energy density conversion not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="energy_density_conversions",
    )
    obj = await update_energy_density_conversion(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{conversion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_energy_density_conversion(
    conversion_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_energy_density_conversion(db, conversion_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Energy density conversion not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="energy_density_conversions",
    )
    ok = await delete_energy_density_conversion(db, conversion_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Energy density conversion not found")
    await db.commit()
    return None
