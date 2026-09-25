from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.interrupted_vehicles import (
    InterruptedVehicleCreate,
    InterruptedVehicleOut,
    InterruptedVehicleUpdate,
)
from crud.interrupted_vehicles import (
    create_interrupted_vehicle,
    delete_interrupted_vehicle,
    get_interrupted_vehicle,
    get_interrupted_vehicle_by_class,
    list_interrupted_vehicles,
    update_interrupted_vehicle,
)

router = APIRouter(prefix="/api/interrupted-vehicles", tags=["interrupted-vehicles"])


@router.get("", response_model=List[InterruptedVehicleOut])
async def get_interrupted_vehicles(
    dataset_revision_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    rows = await list_interrupted_vehicles(db)
    if dataset_revision_id is None:
        return rows
    return [row for row in rows if row.dataset_revision_id == dataset_revision_id]


@router.post("", response_model=InterruptedVehicleOut, status_code=status.HTTP_201_CREATED)
async def create_new_interrupted_vehicle(
    payload: InterruptedVehicleCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="interrupted_vehicles",
    )
    existing = await get_interrupted_vehicle_by_class(
        db, payload.vehicle_class_id, payload.dataset_revision_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interrupted vehicle entry for this vehicle class already exists",
        )
    obj = await create_interrupted_vehicle(db, payload)
    await db.commit()
    rows = await list_interrupted_vehicles(db)
    return next(r for r in rows if r.id == obj.id)


@router.get("/{interrupted_vehicle_id}", response_model=InterruptedVehicleOut)
async def get_interrupted_vehicle_by_id(
    interrupted_vehicle_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_interrupted_vehicle(db, interrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interrupted vehicle not found"
        )
    rows = await list_interrupted_vehicles(db)
    return next((r for r in rows if r.id == interrupted_vehicle_id), obj)


@router.patch("/{interrupted_vehicle_id}", response_model=InterruptedVehicleOut)
async def patch_interrupted_vehicle(
    interrupted_vehicle_id: UUID,
    payload: InterruptedVehicleUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_interrupted_vehicle(db, interrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interrupted vehicle not found"
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="interrupted_vehicles",
    )
    new_class_id = payload.vehicle_class_id or obj.vehicle_class_id
    new_revision_id = payload.dataset_revision_id if payload.dataset_revision_id is not None else obj.dataset_revision_id
    if payload.vehicle_class_id or payload.dataset_revision_id is not None:
        existing = await get_interrupted_vehicle_by_class(db, new_class_id, new_revision_id)
        if existing and existing.id != interrupted_vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interrupted vehicle entry for this vehicle class already exists",
            )
    await update_interrupted_vehicle(db, obj, payload)
    await db.commit()
    rows = await list_interrupted_vehicles(db)
    return next(r for r in rows if r.id == interrupted_vehicle_id)


@router.delete("/{interrupted_vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interrupted_vehicle_by_id(
    interrupted_vehicle_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_interrupted_vehicle(db, interrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interrupted vehicle not found"
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="interrupted_vehicles",
    )
    await delete_interrupted_vehicle(db, obj)
    await db.commit()
