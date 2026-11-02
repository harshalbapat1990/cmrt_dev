from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.waste_treatments import WasteTreatmentCreate, WasteTreatmentOut, WasteTreatmentUpdate
from crud.waste_treatments import (
    create_waste_treatment,
    get_waste_treatment,
    get_waste_treatment_by_name,
    list_waste_treatments,
    update_waste_treatment,
    delete_waste_treatment,
)

router = APIRouter(prefix="/api/waste-treatments", tags=["waste-treatments"])


@router.post("", response_model=WasteTreatmentOut, status_code=status.HTTP_201_CREATED)
async def create_new_waste_treatment(payload: WasteTreatmentCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_waste_treatment_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Waste treatment name already exists")
    obj = await create_waste_treatment(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[WasteTreatmentOut])
async def get_waste_treatments(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_waste_treatments(db, skip, limit, is_active)


@router.get("/{waste_treatment_id}", response_model=WasteTreatmentOut)
async def get_waste_treatment_by_id(waste_treatment_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_waste_treatment(db, waste_treatment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste treatment not found")
    return obj


@router.patch("/{waste_treatment_id}", response_model=WasteTreatmentOut)
async def patch_waste_treatment(
    waste_treatment_id: UUID, payload: WasteTreatmentUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_waste_treatment(db, waste_treatment_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste treatment not found")
    if payload.name:
        existing = await get_waste_treatment_by_name(db, payload.name)
        if existing and existing.id != waste_treatment_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Waste treatment name already exists")
    obj = await update_waste_treatment(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{waste_treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_waste_treatment(waste_treatment_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_waste_treatment(db, waste_treatment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waste treatment not found")
    await db.commit()
    return None
