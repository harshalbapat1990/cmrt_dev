from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.default_waste_rates import (
    DefaultWasteRateCreate,
    DefaultWasteRateOut,
    DefaultWasteRateUpdate,
    DefaultWasteRateWithNamesOut,
)
from crud.default_waste_rates import (
    create_default_waste_rate,
    get_default_waste_rate,
    get_default_waste_rate_with_names,
    list_default_waste_rates,
    list_default_waste_rates_with_names,
    update_default_waste_rate,
    delete_default_waste_rate,
    supersede_default_waste_rate,
)
from crud.audit_logs import write_audit_event

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/default-waste-rates", tags=["default-waste-rates"])


@router.post("", response_model=DefaultWasteRateOut, status_code=status.HTTP_201_CREATED)
async def create_new_default_waste_rate(
    payload: DefaultWasteRateCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="default_waste_rates",
    )
    obj = await create_default_waste_rate(db, payload)
    await write_audit_event(
        db,
        entity_type="default_waste_rate",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    return obj


@router.get("", response_model=List[DefaultWasteRateWithNamesOut])
async def get_default_waste_rates(
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    waste_treatment_id: Optional[UUID] = None,
    as_of_date: Optional[date] = Query(
        None, description="Scenario 8.2 — return only records effective on this date (YYYY-MM-DD)"
    ),
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to rows belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    rows = await list_default_waste_rates_with_names(
        db, jurisdiction_id, material_id, waste_treatment_id, as_of_date, dataset_revision_id, skip, limit
    )
    return [DefaultWasteRateWithNamesOut.model_validate(r) for r in rows]


@router.get("/{record_id}", response_model=DefaultWasteRateOut)
async def get_default_waste_rate_by_id(record_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_default_waste_rate(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Default waste rate not found")
    return obj


@router.patch("/{record_id}", response_model=DefaultWasteRateOut)
async def patch_default_waste_rate(
    record_id: UUID,
    payload: DefaultWasteRateUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_waste_rate(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Default waste rate not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_waste_rates",
    )
    obj = await update_default_waste_rate(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_default_waste_rate(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_waste_rate(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Default waste rate not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_waste_rates",
    )
    ok = await delete_default_waste_rate(db, record_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Default waste rate not found")
    await db.commit()
    return None


@router.post("/{record_id}/supersede", response_model=DefaultWasteRateWithNamesOut)
async def supersede_default_waste_rate_endpoint(
    record_id: UUID,
    payload: DefaultWasteRateUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_default_waste_rate(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste rate not found or already inactive")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="default_waste_rates",
    )
    new_obj = await supersede_default_waste_rate(db, obj, payload.model_dump(exclude_unset=True))
    await write_audit_event(
        db,
        entity_type="default_waste_rate",
        entity_id=new_obj.id,
        action="SUPERSEDE",
        field_name="*",
        old_value=str(record_id),
        new_value=str(new_obj.id),
    )
    await db.commit()
    row = await get_default_waste_rate_with_names(db, new_obj.id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to fetch superseded record")
    return DefaultWasteRateWithNamesOut.model_validate(row)

protect_dataset_reads(router)
