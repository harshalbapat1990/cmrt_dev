from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.audit_logs import write_audit_event
from crud.recycled_content_factors import (
    create_recycled_content_factor,
    delete_recycled_content_factor,
    get_by_jurisdiction_and_source,
    get_recycled_content_factor,
    list_recycled_content_factors,
    update_recycled_content_factor,
    upsert_recycled_content_factor,
)
from schemas.recycled_content_factors import (
    RecycledContentFactorCreate,
    RecycledContentFactorOut,
    RecycledContentFactorUpdate,
    RecycledContentFactorUpsert,
)

router = APIRouter(
    prefix="/api/recycled-content-factors",
    tags=["recycled-content-factors"],
)


@router.get("", response_model=List[RecycledContentFactorOut])
async def list_records(
    jurisdiction_id: Optional[UUID] = Query(None, description="Filter by jurisdiction"),
    emissions_sub_category_id: Optional[UUID] = Query(
        None, description="Filter by emissions sub-category"
    ),
    dataset_revision_id: Optional[UUID] = Query(
        None,
        description="Scope to a dataset revision; omit for global (default) rows",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=10000),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_recycled_content_factors(
        db,
        jurisdiction_id=jurisdiction_id,
        emissions_sub_category_id=emissions_sub_category_id,
        dataset_revision_id=dataset_revision_id,
        skip=skip,
        limit=limit,
    )
    return [RecycledContentFactorOut.model_validate(r) for r in rows]


@router.post("/upsert", response_model=RecycledContentFactorOut)
async def upsert_record(
    payload: RecycledContentFactorUpsert,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="recycled_content_factors",
    )
    obj, created = await upsert_recycled_content_factor(
        db, RecycledContentFactorCreate.model_validate(payload.model_dump())
    )
    await write_audit_event(
        db,
        entity_type="recycled_content_factors",
        entity_id=obj.id,
        action="CREATE" if created else "UPDATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    await db.refresh(obj)
    return RecycledContentFactorOut.model_validate(obj)


@router.get("/{record_id}", response_model=RecycledContentFactorOut)
async def get_record(record_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_recycled_content_factor(db, record_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recycled content factor not found",
        )
    return RecycledContentFactorOut.model_validate(obj)


@router.post("", response_model=RecycledContentFactorOut, status_code=status.HTTP_201_CREATED)
async def create_record(
    payload: RecycledContentFactorCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="recycled_content_factors",
    )
    existing = await get_by_jurisdiction_and_source(
        db,
        jurisdiction_id=payload.jurisdiction_id,
        emissions_source=payload.emissions_source,
        dataset_revision_id=payload.dataset_revision_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A recycled content factor for this jurisdiction, emissions source, "
                "and dataset revision already exists"
            ),
        )
    obj = await create_recycled_content_factor(db, payload)
    await write_audit_event(
        db,
        entity_type="recycled_content_factors",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    await db.refresh(obj)
    return RecycledContentFactorOut.model_validate(obj)


@router.patch("/{record_id}", response_model=RecycledContentFactorOut)
async def patch_record(
    record_id: UUID,
    payload: RecycledContentFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_recycled_content_factor(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recycled content factor not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="recycled_content_factors",
    )
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return RecycledContentFactorOut.model_validate(obj)
    updated = await update_recycled_content_factor(db, obj, payload)
    await write_audit_event(
        db,
        entity_type="recycled_content_factors",
        entity_id=updated.id,
        action="UPDATE",
        field_name=",".join(patch.keys()),
        new_value=str({k: str(v) for k, v in patch.items()}),
    )
    await db.commit()
    await db.refresh(updated)
    return RecycledContentFactorOut.model_validate(updated)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_recycled_content_factor(db, record_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recycled content factor not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="recycled_content_factors",
    )
    ok = await delete_recycled_content_factor(db, record_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recycled content factor not found",
        )
    await write_audit_event(
        db,
        entity_type="recycled_content_factors",
        entity_id=record_id,
        action="DELETE",
        field_name="is_active",
        new_value="false",
    )
    await db.commit()
