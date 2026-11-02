from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.jurisdiction_reporting_stages import (
    JurisdictionReportingStageCreate,
    JurisdictionReportingStageOut,
    JurisdictionReportingStageUpdate,
)
from crud.jurisdiction_reporting_stages import (
    create_jurisdiction_reporting_stage,
    get_jurisdiction_reporting_stage,
    list_jurisdiction_reporting_stages,
    update_jurisdiction_reporting_stage,
    delete_jurisdiction_reporting_stage,
)
from crud.jurisdictions import get_jurisdiction

router = APIRouter(prefix="/api/jurisdiction-reporting-stages", tags=["jurisdiction-reporting-stages"])


@router.post("", response_model=JurisdictionReportingStageOut, status_code=status.HTTP_201_CREATED)
async def create_new_jurisdiction_reporting_stage(
    payload: JurisdictionReportingStageCreate, db: AsyncSession = Depends(get_session)
):
    # Validate jurisdiction exists
    j = await get_jurisdiction(db, payload.jurisdiction_id)
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction not found")
    obj = await create_jurisdiction_reporting_stage(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[JurisdictionReportingStageOut])
async def get_jurisdiction_reporting_stages(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_session)
):
    return await list_jurisdiction_reporting_stages(db, skip, limit)


@router.get("/{stage_id}", response_model=JurisdictionReportingStageOut)
async def get_jurisdiction_reporting_stage_by_id(stage_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_jurisdiction_reporting_stage(db, stage_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction reporting stage not found")
    return obj


@router.patch("/{stage_id}", response_model=JurisdictionReportingStageOut)
async def patch_jurisdiction_reporting_stage(
    stage_id: UUID,
    payload: JurisdictionReportingStageUpdate,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_jurisdiction_reporting_stage(db, stage_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction reporting stage not found")
    obj = await update_jurisdiction_reporting_stage(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_jurisdiction_reporting_stage(stage_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_jurisdiction_reporting_stage(db, stage_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jurisdiction reporting stage not found")
    await db.commit()
    return None
