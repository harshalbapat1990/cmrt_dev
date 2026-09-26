from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.uninterrupted_vehicles import (
    UninterruptedVehicleCreate,
    UninterruptedVehicleOut,
    UninterruptedVehicleUpdate,
)
from crud.uninterrupted_vehicles import (
    create_uninterrupted_vehicle,
    delete_uninterrupted_vehicle,
    get_uninterrupted_vehicle,
    get_uninterrupted_vehicle_by_unique,
    list_uninterrupted_vehicles,
    update_uninterrupted_vehicle,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/uninterrupted-vehicles", tags=["uninterrupted-vehicles"])


@router.get("", response_model=List[UninterruptedVehicleOut])
async def get_uninterrupted_vehicles(
    vehicle_class_id: Optional[UUID] = None,
    gradient_m_per_km: Optional[Decimal] = None,
    curvature_deg_per_km: Optional[Decimal] = None,
    dataset_revision_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    return await list_uninterrupted_vehicles(
        db, vehicle_class_id, gradient_m_per_km, curvature_deg_per_km, dataset_revision_id
    )


@router.post("", response_model=UninterruptedVehicleOut, status_code=status.HTTP_201_CREATED)
async def create_new_uninterrupted_vehicle(
    payload: UninterruptedVehicleCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="uninterrupted_vehicles",
    )
    existing = await get_uninterrupted_vehicle_by_unique(
        db,
        payload.vehicle_class_id,
        payload.gradient_m_per_km,
        payload.curvature_deg_per_km,
        payload.dataset_revision_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Uninterrupted vehicle entry for this (class, gradient, curvature) already exists",
        )
    obj = await create_uninterrupted_vehicle(db, payload)
    await db.commit()
    rows = await list_uninterrupted_vehicles(
        db,
        obj.vehicle_class_id,
        obj.gradient_m_per_km,
        obj.curvature_deg_per_km,
        obj.dataset_revision_id,
    )
    return next(r for r in rows if r.id == obj.id)


@router.get("/{uninterrupted_vehicle_id}", response_model=UninterruptedVehicleOut)
async def get_uninterrupted_vehicle_by_id(
    uninterrupted_vehicle_id: UUID, db: AsyncSession = Depends(get_session)
):
    obj = await get_uninterrupted_vehicle(db, uninterrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Uninterrupted vehicle not found"
        )
    rows = await list_uninterrupted_vehicles(
        db,
        obj.vehicle_class_id,
        obj.gradient_m_per_km,
        obj.curvature_deg_per_km,
        obj.dataset_revision_id,
    )
    return next((r for r in rows if r.id == uninterrupted_vehicle_id), obj)


@router.patch("/{uninterrupted_vehicle_id}", response_model=UninterruptedVehicleOut)
async def patch_uninterrupted_vehicle(
    uninterrupted_vehicle_id: UUID,
    payload: UninterruptedVehicleUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_uninterrupted_vehicle(db, uninterrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Uninterrupted vehicle not found"
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="uninterrupted_vehicles",
    )
    new_class_id = payload.vehicle_class_id or obj.vehicle_class_id
    new_gradient = payload.gradient_m_per_km if payload.gradient_m_per_km is not None else obj.gradient_m_per_km
    new_curvature = payload.curvature_deg_per_km if payload.curvature_deg_per_km is not None else obj.curvature_deg_per_km
    new_revision_id = payload.dataset_revision_id if payload.dataset_revision_id is not None else obj.dataset_revision_id
    if (
        payload.vehicle_class_id
        or payload.gradient_m_per_km is not None
        or payload.curvature_deg_per_km is not None
        or payload.dataset_revision_id is not None
    ):
        existing = await get_uninterrupted_vehicle_by_unique(
            db, new_class_id, new_gradient, new_curvature, new_revision_id
        )
        if existing and existing.id != uninterrupted_vehicle_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Uninterrupted vehicle entry for this (class, gradient, curvature) already exists",
            )
    await update_uninterrupted_vehicle(db, obj, payload)
    await db.commit()
    rows = await list_uninterrupted_vehicles(
        db,
        obj.vehicle_class_id,
        obj.gradient_m_per_km,
        obj.curvature_deg_per_km,
        obj.dataset_revision_id,
    )
    return next(r for r in rows if r.id == uninterrupted_vehicle_id)


@router.delete("/{uninterrupted_vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_uninterrupted_vehicle_by_id(
    uninterrupted_vehicle_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_uninterrupted_vehicle(db, uninterrupted_vehicle_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Uninterrupted vehicle not found"
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="uninterrupted_vehicles",
    )
    await delete_uninterrupted_vehicle(db, obj)
    await db.commit()

protect_dataset_reads(router)
