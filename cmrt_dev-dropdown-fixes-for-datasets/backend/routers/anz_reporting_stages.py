from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.anz_reporting_stages import (
    AnzReportingStageCreate,
    AnzReportingStageOut,
    AnzReportingStageUpdate,
)
from crud.anz_reporting_stages import (
    create_anz_reporting_stage,
    get_anz_reporting_stage,
    get_anz_reporting_stage_by_name,
    list_anz_reporting_stages,
    update_anz_reporting_stage,
    delete_anz_reporting_stage,
)

router = APIRouter(prefix="/api/anz-reporting-stages", tags=["anz-reporting-stages"])


@router.post("", response_model=AnzReportingStageOut, status_code=status.HTTP_201_CREATED)
async def create_new_anz_reporting_stage(
    payload: AnzReportingStageCreate, db: AsyncSession = Depends(get_session)
):
    existing = await get_anz_reporting_stage_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stage name already exists")
    obj = await create_anz_reporting_stage(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[AnzReportingStageOut])
async def get_anz_reporting_stages(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_session)):
    return await list_anz_reporting_stages(db, skip, limit)


@router.get("/{stage_id}", response_model=AnzReportingStageOut)
async def get_anz_reporting_stage_by_id(stage_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_anz_reporting_stage(db, stage_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ANZ reporting stage not found")
    return obj


@router.patch("/{stage_id}", response_model=AnzReportingStageOut)
async def patch_anz_reporting_stage(
    stage_id: UUID, payload: AnzReportingStageUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_anz_reporting_stage(db, stage_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ANZ reporting stage not found")
    if payload.name:
        existing = await get_anz_reporting_stage_by_name(db, payload.name)
        if existing and existing.id != stage_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stage name already exists")
    obj = await update_anz_reporting_stage(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_anz_reporting_stage(stage_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_anz_reporting_stage(db, stage_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ANZ reporting stage not found")
    await db.commit()
    return None
