from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.vehicle_energy_conversion_rates import (
    VehicleEnergyConversionRateCreate,
    VehicleEnergyConversionRateOut,
    VehicleEnergyConversionRateUpdate,
)
from crud.vehicle_energy_conversion_rates import (
    create_vehicle_energy_conversion_rate,
    delete_vehicle_energy_conversion_rate,
    get_vehicle_energy_conversion_rate,
    get_vehicle_energy_conversion_rate_by_class,
    list_vehicle_energy_conversion_rates,
    update_vehicle_energy_conversion_rate,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(
    prefix="/api/vehicle-energy-conversion-rates",
    tags=["vehicle-energy-conversion-rates"],
)


@router.get("", response_model=List[VehicleEnergyConversionRateOut])
async def get_vehicle_energy_conversion_rates(
    dataset_revision_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    return await list_vehicle_energy_conversion_rates(db, dataset_revision_id)


@router.post(
    "", response_model=VehicleEnergyConversionRateOut, status_code=status.HTTP_201_CREATED
)
async def create_new_vehicle_energy_conversion_rate(
    payload: VehicleEnergyConversionRateCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="vehicle_energy_conversion_rates",
    )
    existing = await get_vehicle_energy_conversion_rate_by_class(
        db, payload.vehicle_class_id, payload.dataset_revision_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Energy conversion rate for this vehicle class already exists",
        )
    obj = await create_vehicle_energy_conversion_rate(db, payload)
    await db.commit()
    rows = await list_vehicle_energy_conversion_rates(db, obj.dataset_revision_id)
    return next(r for r in rows if r.id == obj.id)


@router.get("/{rate_id}", response_model=VehicleEnergyConversionRateOut)
async def get_vehicle_energy_conversion_rate_by_id(
    rate_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_vehicle_energy_conversion_rate(db, rate_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle energy conversion rate not found",
        )
    rows = await list_vehicle_energy_conversion_rates(db, obj.dataset_revision_id)
    return next((r for r in rows if r.id == rate_id), obj)


@router.patch("/{rate_id}", response_model=VehicleEnergyConversionRateOut)
async def patch_vehicle_energy_conversion_rate(
    rate_id: UUID,
    payload: VehicleEnergyConversionRateUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_vehicle_energy_conversion_rate(db, rate_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle energy conversion rate not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="vehicle_energy_conversion_rates",
    )
    new_class_id = payload.vehicle_class_id or obj.vehicle_class_id
    new_revision_id = payload.dataset_revision_id if payload.dataset_revision_id is not None else obj.dataset_revision_id
    if payload.vehicle_class_id or payload.dataset_revision_id is not None:
        existing = await get_vehicle_energy_conversion_rate_by_class(db, new_class_id, new_revision_id)
        if existing and existing.id != rate_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Energy conversion rate for this vehicle class already exists",
            )
    await update_vehicle_energy_conversion_rate(db, obj, payload)
    await db.commit()
    rows = await list_vehicle_energy_conversion_rates(db, obj.dataset_revision_id)
    return next(r for r in rows if r.id == rate_id)


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_energy_conversion_rate_by_id(
    rate_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_vehicle_energy_conversion_rate(db, rate_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle energy conversion rate not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="vehicle_energy_conversion_rates",
    )
    await delete_vehicle_energy_conversion_rate(db, obj)
    await db.commit()

protect_dataset_reads(router)
