
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_principal, Principal
from core.session import get_session
from crud.project import touch_project
from crud.audit_logs import write_audit_event

from schemas.emissions_entries import (
    EmissionEntryOut, EmissionEntryCreate, EmissionEntryUpdate,
    EmissionEntrySummaryOut, EmissionEntrySummaryCreate, EmissionEntrySummaryUpdate
)
from crud.emissions_entries import (
    create_entry, get_entry, list_entries, update_entry, delete_entry,
    create_summary, upsert_summary, get_summary, list_summaries, update_summary, delete_summary
)

router = APIRouter(prefix="/api/emission_entries", tags=["emission_entries"])

# ---------- Emission Entries ----------
@router.post("/post-emission-entries", response_model=EmissionEntryOut, status_code=status.HTTP_201_CREATED)
async def create_emission_entry(
    payload: EmissionEntryCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await create_entry(db, payload)
    await touch_project(db, payload.project_id)
    await write_audit_event(
        db,
        entity_type="emission_entry",
        entity_id=obj.id,
        action="CREATE",
        entity_name="Emission entry",
        metadata={"project_id": str(payload.project_id)},
    )
    await db.commit()
    return obj

@router.get("/get-emission-entries", response_model=List[EmissionEntryOut])
async def get_emission_entries(
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    project_reporting_submission_id: Optional[UUID] = None,
    emission_source_id: Optional[UUID] = None,
    emissions_sub_category_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    objs = await list_entries(db, skip, limit, project_id, project_reporting_submission_id, emission_source_id, emissions_sub_category_id)
    return objs

@router.get("/get-emission-entries-byid/{id}", response_model=EmissionEntryOut)
async def get_emission_entry_by_id(id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_entry(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry not found")
    return obj

@router.patch("/patch-emission-entries/{id}", response_model=EmissionEntryOut)
async def patch_emission_entry(
    id: UUID,
    payload: EmissionEntryUpdate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_entry(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry not found")
    obj = await update_entry(db, obj, payload)
    await touch_project(db, obj.project_id)
    await write_audit_event(
        db,
        entity_type="emission_entry",
        entity_id=id,
        action="UPDATE",
        entity_name="Emission entry",
        metadata={"project_id": str(obj.project_id)},
    )
    await db.commit()
    return obj

@router.delete("/emission-entries/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_emission_entry(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_entry(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry not found")
    project_id = obj.project_id
    await write_audit_event(
        db,
        entity_type="emission_entry",
        entity_id=id,
        action="DELETE",
        entity_name="Emission entry",
        metadata={"project_id": str(project_id)},
    )
    ok = await delete_entry(db, id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry not found")
    await touch_project(db, project_id)
    await db.commit()
    return None

# ---------- Emission Entry Summaries ----------
@router.post("/summaries", response_model=EmissionEntrySummaryOut, status_code=status.HTTP_201_CREATED)
async def create_emission_entry_summary(payload: EmissionEntrySummaryCreate, db: AsyncSession = Depends(get_session)):
    obj = await create_summary(db, payload)
    await touch_project(db, payload.project_id)
    await db.commit()
    return obj
# Router - Make the composite key explicit
@router.put(
    "/summaries/upsert/{project_id}/{project_reporting_submission_id}", 
    response_model=EmissionEntrySummaryOut
)
async def upsert_emission_entry_summary(
    project_id: UUID, 
    project_reporting_submission_id: UUID,
    payload: EmissionEntrySummaryCreate, 
    db: AsyncSession = Depends(get_session)
):
    obj = await upsert_summary(db, project_id, project_reporting_submission_id, payload)
    await touch_project(db, project_id)
    await db.commit()
    return obj

@router.get("/summaries", response_model=List[EmissionEntrySummaryOut])
async def get_emission_entry_summaries(
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    project_reporting_submission_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    objs = await list_summaries(db, skip, limit, project_id, project_reporting_submission_id)
    return objs

@router.get("/summaries/{id}", response_model=EmissionEntrySummaryOut)
async def get_emission_entry_summary_by_id(id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry summary not found")
    return obj

@router.patch("/summaries/{id}", response_model=EmissionEntrySummaryOut)
async def patch_emission_entry_summary(id: UUID, payload: EmissionEntrySummaryUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry summary not found")
    obj = await update_summary(db, obj, payload)
    await touch_project(db, obj.project_id)
    await db.commit()
    return obj

@router.delete("/summaries/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_emission_entry_summary(id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry summary not found")
    project_id = obj.project_id
    ok = await delete_summary(db, id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emission entry summary not found")
    await touch_project(db, project_id)
    await db.commit()
    return None
