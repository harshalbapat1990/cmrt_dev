from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.audit_logs import write_audit_event
from crud.renewable_energy_classification import (
    create_renewable_energy_classification,
    delete_renewable_energy_classification,
    get_by_source,
    get_renewable_energy_classification,
    list_renewable_energy_classifications,
    update_renewable_energy_classification,
)
from schemas.renewable_energy_classification import (
    RenewableEnergyClassificationCreate,
    RenewableEnergyClassificationOut,
    RenewableEnergyClassificationUpdate,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(
    prefix="/api/renewable-energy-classifications",
    tags=["renewable-energy-classifications"],
)


@router.get("", response_model=List[RenewableEnergyClassificationOut])
async def list_records(
    dataset_revision_id: Optional[UUID] = Query(
        None,
        description="Scope to a dataset revision; omit for global (default) rows",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_renewable_energy_classifications(
        db,
        dataset_revision_id=dataset_revision_id,
        skip=skip,
        limit=limit,
    )
    return [RenewableEnergyClassificationOut.model_validate(r) for r in rows]


@router.get("/{record_id}", response_model=RenewableEnergyClassificationOut)
async def get_record(record_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_renewable_energy_classification(db, record_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Renewable energy classification not found",
        )
    return RenewableEnergyClassificationOut.model_validate(obj)


@router.post(
    "", response_model=RenewableEnergyClassificationOut, status_code=status.HTTP_201_CREATED
)
async def create_record(
    payload: RenewableEnergyClassificationCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="renewable_energy_classification",
    )
    existing = await get_by_source(
        db,
        emissions_source=payload.emissions_source,
        dataset_revision_id=payload.dataset_revision_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A renewable energy classification for this emissions source "
                "and dataset revision already exists"
            ),
        )
    obj = await create_renewable_energy_classification(db, payload)
    await write_audit_event(
        db,
        entity_type="renewable_energy_classifications",
        entity_id=obj.id,
        action="CREATE",
        field_name="*",
        new_value=str(payload.model_dump()),
    )
    await db.commit()
    await db.refresh(obj)
    return RenewableEnergyClassificationOut.model_validate(obj)


@router.patch("/{record_id}", response_model=RenewableEnergyClassificationOut)
async def patch_record(
    record_id: UUID,
    payload: RenewableEnergyClassificationUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_renewable_energy_classification(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Renewable energy classification not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="renewable_energy_classification",
    )
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return RenewableEnergyClassificationOut.model_validate(obj)
    updated = await update_renewable_energy_classification(db, obj, payload)
    await write_audit_event(
        db,
        entity_type="renewable_energy_classifications",
        entity_id=updated.id,
        action="UPDATE",
        field_name=",".join(patch.keys()),
        new_value=str({k: str(v) for k, v in patch.items()}),
    )
    await db.commit()
    await db.refresh(updated)
    return RenewableEnergyClassificationOut.model_validate(updated)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_renewable_energy_classification(db, record_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Renewable energy classification not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="renewable_energy_classification",
    )
    ok = await delete_renewable_energy_classification(db, record_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Renewable energy classification not found",
        )
    await write_audit_event(
        db,
        entity_type="renewable_energy_classifications",
        entity_id=record_id,
        action="DELETE",
        field_name="is_active",
        new_value="false",
    )
    await db.commit()

protect_dataset_reads(router)
