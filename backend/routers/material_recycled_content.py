from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.material_recycled_content import (
    MaterialRecycledContentCreate,
    MaterialRecycledContentOut,
    MaterialRecycledContentUpdate,
    MaterialRecycledContentWithNamesOut,
)
from crud.material_recycled_content import (
    create_material_recycled_content,
    get_material_recycled_content,
    get_material_recycled_content_by_jurisdiction_and_material,
    get_material_recycled_content_with_names,
    list_material_recycled_contents,
    list_material_recycled_contents_with_names,
    update_material_recycled_content,
    delete_material_recycled_content,
    supersede_material_recycled_content,
    compute_blended_ef,
)
from crud.audit_logs import write_audit_event

router = APIRouter(prefix="/api/material-recycled-content", tags=["material-recycled-content"])


class BlendedEFOut(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    material_id: UUID
    recycled_from_material_id: UUID
    percent: Decimal
    grade_id: Optional[int] = None
    band_code: Optional[str] = None
    metric_type_code: Optional[str] = None
    unit_code: Optional[str] = None
    ef_virgin: Optional[Decimal] = None
    ef_recycled: Optional[Decimal] = None
    ef_blended: Optional[Decimal] = None


@router.post("", response_model=MaterialRecycledContentOut, status_code=status.HTTP_201_CREATED)
async def create_record(
    payload: MaterialRecycledContentCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="material_recycled_content",
    )
    existing = await get_material_recycled_content_by_jurisdiction_and_material(
        db, payload.jurisdiction_id, payload.material_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recycled content record for this jurisdiction and material already exists",
        )
    obj = await create_material_recycled_content(db, payload)
    await write_audit_event(
        db,
        entity_type="material_recycled_content",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    return obj


@router.get("", response_model=List[MaterialRecycledContentWithNamesOut])
async def list_records(
    material_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    as_of_date: Optional[date] = Query(
        None,
        description="Scenario 7.4 — return only records effective on this date (YYYY-MM-DD)",
    ),
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to rows belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    rows = await list_material_recycled_contents_with_names(
        db, material_id, jurisdiction_id, as_of_date, dataset_revision_id, skip, limit
    )
    return [MaterialRecycledContentWithNamesOut.model_validate(r) for r in rows]


@router.get("/{record_id}", response_model=MaterialRecycledContentOut)
async def get_record(record_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_material_recycled_content(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return obj


@router.patch("/{record_id}", response_model=MaterialRecycledContentOut)
async def patch_record(
    record_id: UUID,
    payload: MaterialRecycledContentUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_material_recycled_content(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="material_recycled_content",
    )
    obj = await update_material_recycled_content(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_material_recycled_content(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="material_recycled_content",
    )
    ok = await delete_material_recycled_content(db, record_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await db.commit()
    return None


@router.post("/{record_id}/supersede", response_model=MaterialRecycledContentWithNamesOut)
async def supersede_record(
    record_id: UUID,
    payload: MaterialRecycledContentUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_material_recycled_content(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found or already inactive")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="material_recycled_content",
    )
    new_obj = await supersede_material_recycled_content(db, obj, payload.model_dump(exclude_unset=True))
    new_obj = await supersede_material_recycled_content(db, obj, payload.model_dump(exclude_unset=True))
    await write_audit_event(
        db,
        entity_type="material_recycled_content",
        entity_id=new_obj.id,
        action="SUPERSEDE",
        field_name="*",
        old_value=str(record_id),
        new_value=str(new_obj.id),
    )
    await db.commit()
    row = await get_material_recycled_content_with_names(db, new_obj.id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to fetch superseded record")
    return MaterialRecycledContentWithNamesOut.model_validate(row)



@router.get("/blended-ef", response_model=List[BlendedEFOut])
async def get_blended_ef(
    material_id: UUID = Query(..., description="Material A whose blended EF to compute"),
    factor_set_id: UUID = Query(..., description="Emissions factor set to look up EF values from"),
    metric_type_code: str = Query(..., description="e.g. emission_intensity_a1_a3"),
    jurisdiction_id: Optional[UUID] = Query(None),
    as_of_date: Optional[date] = Query(
        None,
        description="Effective date for recycled-content record lookup",
    ),
    db: AsyncSession = Depends(get_session),
):
    rows = await compute_blended_ef(
        db,
        material_id=material_id,
        factor_set_id=factor_set_id,
        metric_type_code=metric_type_code,
        jurisdiction_id=jurisdiction_id,
        as_of_date=as_of_date,
    )
    return [
        BlendedEFOut(
            material_id=r.material_id,
            recycled_from_material_id=r.recycled_from_material_id,
            percent=r.percent,
            grade_id=r.grade_id,
            band_code=r.band_code,
            metric_type_code=r.metric_type_code,
            unit_code=r.unit_code,
            ef_virgin=r.ef_virgin,
            ef_recycled=r.ef_recycled,
            ef_blended=r.ef_blended,
        )
        for r in rows
    ]

