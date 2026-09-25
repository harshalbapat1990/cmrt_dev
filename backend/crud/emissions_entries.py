
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.emissions_entries import EmissionEntry, EmissionEntrySummary
from schemas.emissions_entries import (
    EmissionEntryCreate, EmissionEntryUpdate,
    EmissionEntrySummaryCreate, EmissionEntrySummaryUpdate
)

# ---------- EmissionEntry ----------
async def create_entry(db: AsyncSession, payload: EmissionEntryCreate) -> EmissionEntry:
    obj = EmissionEntry(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_entry(db: AsyncSession, entry_id: UUID) -> Optional[EmissionEntry]:
    res = await db.execute(select(EmissionEntry).where(EmissionEntry.id == entry_id))
    return res.scalar_one_or_none()

async def list_entries(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    project_reporting_submission_id: Optional[UUID] = None,
    emission_source_id: Optional[UUID] = None,
    emissions_sub_category_id: Optional[UUID] = None,
) -> List[EmissionEntry]:
    q = select(EmissionEntry)
    if project_id:
        q = q.where(EmissionEntry.project_id == project_id)
    if project_reporting_submission_id:
        q = q.where(EmissionEntry.project_reporting_submission_id == project_reporting_submission_id)
    if emission_source_id:
        q = q.where(EmissionEntry.emission_source_id == emission_source_id)
    if emissions_sub_category_id:
        q = q.where(EmissionEntry.emissions_sub_category_id == emissions_sub_category_id)
    q = q.offset(skip).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()

async def update_entry(db: AsyncSession, entry: EmissionEntry, payload: EmissionEntryUpdate) -> EmissionEntry:
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(entry, k, v)
    entry.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(entry)
    return entry

async def delete_entry(db: AsyncSession, entry_id: UUID) -> bool:
    res = await db.execute(delete(EmissionEntry).where(EmissionEntry.id == entry_id))
    return res.rowcount > 0

# ---------- EmissionEntrySummary ----------
async def create_summary(db: AsyncSession, payload: EmissionEntrySummaryCreate) -> EmissionEntrySummary:
    # Uniqueness: one summary per (project_id, project_reporting_submission_id)
    existing = await db.execute(
        select(EmissionEntrySummary).where(
            (EmissionEntrySummary.project_id == payload.project_id) &
            (EmissionEntrySummary.project_reporting_submission_id == payload.project_reporting_submission_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Summary already exists for this project & reporting submission."
        )
    obj = EmissionEntrySummary(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def upsert_summary(
    db: AsyncSession, 
    project_id: UUID,
    project_reporting_submission_id: UUID,
    payload: EmissionEntrySummaryCreate
) -> EmissionEntrySummary:
    res = await db.execute(
        select(EmissionEntrySummary).where(
            (EmissionEntrySummary.project_id == project_id) &
            (EmissionEntrySummary.project_reporting_submission_id == project_reporting_submission_id)
        )
    )
    obj = res.scalar_one_or_none()
    if obj:
        obj.summary = payload.summary
        obj.submitted_by_user_id = payload.submitted_by_user_id
        obj.updated_on = datetime.utcnow()
        await db.flush()
        await db.refresh(obj)
        return obj
    
    # Create new with explicit IDs
    obj = EmissionEntrySummary(
        project_id=project_id,
        project_reporting_submission_id=project_reporting_submission_id,
        **payload.model_dump()
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_summary(db: AsyncSession, summary_id: UUID) -> Optional[EmissionEntrySummary]:
    res = await db.execute(select(EmissionEntrySummary).where(EmissionEntrySummary.id == summary_id))
    return res.scalar_one_or_none()

async def list_summaries(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    project_reporting_submission_id: Optional[UUID] = None,
) -> List[EmissionEntrySummary]:
    q = select(EmissionEntrySummary)
    if project_id:
        q = q.where(EmissionEntrySummary.project_id == project_id)
    if project_reporting_submission_id:
        q = q.where(EmissionEntrySummary.project_reporting_submission_id == project_reporting_submission_id)
    q = q.offset(skip).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()

async def update_summary(db: AsyncSession, summary: EmissionEntrySummary, payload: EmissionEntrySummaryUpdate) -> EmissionEntrySummary:
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(summary, k, v)
    summary.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(summary)
    return summary

async def delete_summary(db: AsyncSession, summary_id: UUID) -> bool:
    res = await db.execute(delete(EmissionEntrySummary).where(EmissionEntrySummary.id == summary_id))
    return res.rowcount > 0
