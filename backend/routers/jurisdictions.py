from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.jurisdictions import JurisdictionCreate, JurisdictionOut, JurisdictionUpdate
from schemas.jurisdiction_reporting_stages import JurisdictionReportingStageOut
from crud.jurisdictions import (
    create_jurisdiction,
    get_jurisdiction,
    get_jurisdiction_by_name,
    list_jurisdictions,
    update_jurisdiction,
    delete_jurisdiction,
)
from crud.jurisdiction_reporting_stages import (
    list_jurisdiction_reporting_stages_by_jurisdiction,
)

router = APIRouter(prefix="/api/jurisdictions", tags=["jurisdictions"])


@router.post("", response_model=JurisdictionOut, status_code=status.HTTP_201_CREATED)
async def create_new_jurisdiction(payload: JurisdictionCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_jurisdiction_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Jurisdiction name already exists")
    obj = await create_jurisdiction(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[JurisdictionOut])
async def get_jurisdictions(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    type: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get jurisdictions with optional filtering by name, type, and/or parent_id (for regions of a country)."""
    if name and type:
        # Get single jurisdiction by name and type
        from schemas.jurisdictions import JurisdictionOut
        obj = await get_jurisdiction_by_name(db, name, type)
        if obj:
            return [JurisdictionOut.model_validate(obj)]
        return []
    elif name:
        # Get single jurisdiction by name only
        obj = await get_jurisdiction_by_name(db, name)
        if obj:
            return [JurisdictionOut.model_validate(obj)]
        return []
    else:
        # Get all jurisdictions with optional type and parent_id filters
        return await list_jurisdictions(db, skip, limit, type, parent_id)


@router.get("/{jurisdiction_id}", response_model=JurisdictionOut)
async def get_jurisdiction_by_id(jurisdiction_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_jurisdiction(db, jurisdiction_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    return obj


@router.patch("/{jurisdiction_id}", response_model=JurisdictionOut)
async def patch_jurisdiction(
    jurisdiction_id: UUID, payload: JurisdictionUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_jurisdiction(db, jurisdiction_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    if payload.name:
        existing = await get_jurisdiction_by_name(db, payload.name)
        if existing and existing.id != jurisdiction_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Jurisdiction name already exists")
    obj = await update_jurisdiction(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{jurisdiction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_jurisdiction(jurisdiction_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_jurisdiction(db, jurisdiction_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    await db.commit()
    return None


@router.get("/{jurisdiction_id}/reporting-stages", response_model=List[JurisdictionReportingStageOut])
async def get_reporting_stages_for_jurisdiction(
    jurisdiction_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_jurisdiction(db, jurisdiction_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    return await list_jurisdiction_reporting_stages_by_jurisdiction(db, jurisdiction_id, skip, limit)
