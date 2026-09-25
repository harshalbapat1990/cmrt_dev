from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.default_transport_distances import (
    DefaultTransportDistanceCreate,
    DefaultTransportDistanceOut,
    DefaultTransportDistanceUpdate,
    DefaultTransportDistanceWithNamesOut,
)
from crud.default_transport_distances import (
    create_default_transport_distance,
    get_default_transport_distance,
    get_default_transport_distance_by_key,
    get_default_transport_distance_with_names,
    list_default_transport_distances,
    list_default_transport_distances_with_names,
    update_default_transport_distance,
    delete_default_transport_distance,
    supersede_default_transport_distance,
)
from crud.audit_logs import write_audit_event

router = APIRouter(prefix="/api/default-transport-distances", tags=["default-transport-distances"])


@router.post("", response_model=DefaultTransportDistanceOut, status_code=status.HTTP_201_CREATED)
async def create_new_default_transport_distance(
    payload: DefaultTransportDistanceCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="default_transport_distances",
    )
    existing = await get_default_transport_distance_by_key(
        db, payload.jurisdiction_id, payload.material_id, payload.emissions_category_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transport distance entry for this jurisdiction and material/category already exists",
        )
    obj = await create_default_transport_distance(db, payload)
    await write_audit_event(
        db,
        entity_type="default_transport_distance",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    return obj


@router.get("", response_model=List[DefaultTransportDistanceWithNamesOut])
async def get_default_transport_distances(
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    emissions_category_id: Optional[UUID] = None,
    as_of_date: Optional[date] = Query(
        None, description="Scenario 8.1 — return only records effective on this date (YYYY-MM-DD)"
    ),
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to rows belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    rows = await list_default_transport_distances_with_names(
        db, jurisdiction_id, material_id, emissions_category_id, as_of_date, dataset_revision_id, skip, limit
    )
    return [DefaultTransportDistanceWithNamesOut.model_validate(r) for r in rows]


@router.get("/{record_id}", response_model=DefaultTransportDistanceOut)
async def get_default_transport_distance_by_id(record_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_default_transport_distance(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return obj


@router.patch("/{record_id}", response_model=DefaultTransportDistanceOut)
async def patch_default_transport_distance(
    record_id: UUID,
    payload: DefaultTransportDistanceUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_transport_distance(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_transport_distances",
    )
    obj = await update_default_transport_distance(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_default_transport_distance(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_transport_distance(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_transport_distances",
    )
    ok = await delete_default_transport_distance(db, record_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await db.commit()
    return None


@router.post("/{record_id}/supersede", response_model=DefaultTransportDistanceWithNamesOut)
async def supersede_default_transport_distance_endpoint(
    record_id: UUID,
    payload: DefaultTransportDistanceUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_transport_distance(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found or already inactive")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_transport_distances",
    )
    new_obj = await supersede_default_transport_distance(db, obj, payload.model_dump(exclude_unset=True))
    await write_audit_event(
        db,
        entity_type="default_transport_distance",
        entity_id=new_obj.id,
        action="SUPERSEDE",
        field_name="*",
        old_value=str(record_id),
        new_value=str(new_obj.id),
    )
    await db.commit()
    row = await get_default_transport_distance_with_names(db, new_obj.id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to fetch superseded record")
    return DefaultTransportDistanceWithNamesOut.model_validate(row)
