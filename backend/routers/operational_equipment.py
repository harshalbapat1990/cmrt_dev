from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.audit_logs import write_audit_event
from crud.operational_equipment import (
    create_operational_equipment,
    delete_operational_equipment,
    get_operational_equipment,
    get_operational_equipment_by_item,
    list_operational_equipment,
    supersede_operational_equipment,
)
from crud.project_dataset_revisions import list_project_dataset_revisions_by_project
from crud.dataset_revisions import get_published_dataset_revision
from schemas.operational_equipment import (
    OperationalEquipmentCreate,
    OperationalEquipmentOut,
    OperationalEquipmentUpdate,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/operational-equipment", tags=["operational-equipment"])


@router.get("", response_model=List[OperationalEquipmentOut])
async def get_operational_equipment_list(
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to rows belonging to a specific dataset revision; omit for global rows"
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Project context used to resolve dataset revision when dataset_revision_id is omitted",
    ),
    skip: int = 0,
    limit: int = 500,
    db: AsyncSession = Depends(get_session),
):
    resolved_dataset_revision_id = dataset_revision_id
    if resolved_dataset_revision_id is None and project_id is not None:
        project_revisions = await list_project_dataset_revisions_by_project(db, project_id)
        if project_revisions:
            resolved_dataset_revision_id = project_revisions[0].dataset_revision_id

    if resolved_dataset_revision_id is None:
        published_default = await get_published_dataset_revision(db)
        if published_default is not None:
            resolved_dataset_revision_id = published_default.id

    return await list_operational_equipment(db, resolved_dataset_revision_id, skip, limit)


@router.post("", response_model=OperationalEquipmentOut, status_code=status.HTTP_201_CREATED)
async def create_new_operational_equipment(
    payload: OperationalEquipmentCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="operational_equipment",
    )
    existing = await get_operational_equipment_by_item(db, payload.item, payload.dataset_revision_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active operational equipment row with item '{payload.item}' already exists",
        )
    obj = await create_operational_equipment(db, payload)
    await write_audit_event(
        db,
        entity_type="operational_equipment",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{record_id}/supersede", response_model=OperationalEquipmentOut)
async def supersede_operational_equipment_endpoint(
    record_id: UUID,
    payload: OperationalEquipmentUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_operational_equipment(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found or already inactive")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="operational_equipment",
    )

    patch = payload.model_dump(exclude_unset=True)
    new_obj = await supersede_operational_equipment(db, obj, patch)
    await write_audit_event(
        db,
        entity_type="operational_equipment",
        entity_id=new_obj.id,
        action="SUPERSEDE",
        field_name="*",
        old_value=str(record_id),
        new_value=str(new_obj.id),
    )
    await db.commit()
    await db.refresh(new_obj)
    return new_obj


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operational_equipment_endpoint(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_operational_equipment(db, record_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="operational_equipment",
    )
    ok = await delete_operational_equipment(db, record_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await db.commit()
    return None

protect_dataset_reads(router)
