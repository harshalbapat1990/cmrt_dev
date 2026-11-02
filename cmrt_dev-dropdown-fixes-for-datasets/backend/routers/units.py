from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.units import UnitCreate, UnitOut, UnitUpdate
from crud.units import (
    create_unit,
    get_unit,
    get_unit_by_code,
    list_units,
    update_unit,
    delete_unit,
)

router = APIRouter(prefix="/api/units", tags=["units"])


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
async def create_new_unit(payload: UnitCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_unit_by_code(db, payload.code)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit code already exists")
    obj = await create_unit(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[UnitOut])
async def get_units(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_session)):
    return await list_units(db, skip, limit)


@router.get("/{unit_id}", response_model=UnitOut)
async def get_unit_by_id(unit_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_unit(db, unit_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return obj


@router.patch("/{unit_id}", response_model=UnitOut)
async def patch_unit(unit_id: UUID, payload: UnitUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_unit(db, unit_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    if payload.code:
        existing = await get_unit_by_code(db, payload.code)
        if existing and existing.id != unit_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit code already exists")
    obj = await update_unit(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_unit(unit_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_unit(db, unit_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    await db.commit()
    return None
