from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.vehicle_classes import VehicleClassCreate, VehicleClassOut, VehicleClassUpdate
from crud.vehicle_classes import (
    create_vehicle_class,
    delete_vehicle_class,
    get_vehicle_class,
    list_vehicle_classes,
    update_vehicle_class,
)

router = APIRouter(prefix="/api/vehicle-classes", tags=["vehicle-classes"])


@router.get("", response_model=List[VehicleClassOut])
async def get_vehicle_classes(db: AsyncSession = Depends(get_session)):
    return await list_vehicle_classes(db)


@router.post("", response_model=VehicleClassOut, status_code=status.HTTP_201_CREATED)
async def create_new_vehicle_class(
    payload: VehicleClassCreate, db: AsyncSession = Depends(get_session)
):
    obj = await create_vehicle_class(db, payload)
    await db.commit()
    return obj


@router.get("/{vehicle_class_id}", response_model=VehicleClassOut)
async def get_vehicle_class_by_id(
    vehicle_class_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_vehicle_class(db, vehicle_class_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle class not found")
    return obj


@router.patch("/{vehicle_class_id}", response_model=VehicleClassOut)
async def patch_vehicle_class(
    vehicle_class_id: UUID,
    payload: VehicleClassUpdate,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_vehicle_class(db, vehicle_class_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle class not found")
    obj = await update_vehicle_class(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{vehicle_class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_class_by_id(
    vehicle_class_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_vehicle_class(db, vehicle_class_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle class not found")
    await delete_vehicle_class(db, obj)
    await db.commit()
