from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.vehicle_masses import VehicleMassCreate, VehicleMassOut, VehicleMassUpdate
from crud.vehicle_masses import (
    create_vehicle_mass,
    delete_vehicle_mass,
    get_vehicle_mass,
    get_vehicle_mass_by_class,
    list_vehicle_masses,
    update_vehicle_mass,
)

router = APIRouter(prefix="/api/vehicle-masses", tags=["vehicle-masses"])


@router.get("", response_model=List[VehicleMassOut])
async def get_vehicle_masses(db: AsyncSession = Depends(get_session)):
    return await list_vehicle_masses(db)


@router.post("", response_model=VehicleMassOut, status_code=status.HTTP_201_CREATED)
async def create_new_vehicle_mass(
    payload: VehicleMassCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="vehicle_masses",
    )
    existing = await get_vehicle_mass_by_class(db, payload.vehicle_class_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle mass entry for this vehicle class already exists",
        )
    obj = await create_vehicle_mass(db, payload)
    await db.commit()
    return (await list_vehicle_masses(db))[-1]


@router.get("/{vehicle_mass_id}", response_model=VehicleMassOut)
async def get_vehicle_mass_by_id(
    vehicle_mass_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_vehicle_mass(db, vehicle_mass_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle mass not found")
    rows = await list_vehicle_masses(db)
    row = next((r for r in rows if r.id == vehicle_mass_id), None)
    return row or obj


@router.patch("/{vehicle_mass_id}", response_model=VehicleMassOut)
async def patch_vehicle_mass(
    vehicle_mass_id: UUID,
    payload: VehicleMassUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="vehicle_masses",
    )
    obj = await get_vehicle_mass(db, vehicle_mass_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle mass not found")
    if payload.vehicle_class_id and payload.vehicle_class_id != obj.vehicle_class_id:
        existing = await get_vehicle_mass_by_class(db, payload.vehicle_class_id)
        if existing and existing.id != vehicle_mass_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vehicle mass entry for this vehicle class already exists",
            )
    await update_vehicle_mass(db, obj, payload)
    await db.commit()
    rows = await list_vehicle_masses(db)
    return next(r for r in rows if r.id == vehicle_mass_id)


@router.delete("/{vehicle_mass_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_mass_by_id(
    vehicle_mass_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="vehicle_masses",
    )
    obj = await get_vehicle_mass(db, vehicle_mass_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle mass not found")
    await delete_vehicle_mass(db, obj)
    await db.commit()
