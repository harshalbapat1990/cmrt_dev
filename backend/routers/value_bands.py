from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.value_bands import ValueBandCreate, ValueBandOut, ValueBandUpdate
from crud.value_bands import (
    create_value_band,
    get_value_band,
    list_value_bands,
    update_value_band,
    delete_value_band,
)

router = APIRouter(prefix="/api/value-bands", tags=["value-bands"])


@router.post("", response_model=ValueBandOut, status_code=status.HTTP_201_CREATED)
async def create_new_value_band(payload: ValueBandCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_value_band(db, payload.code)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Value band code already exists")
    obj = await create_value_band(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[ValueBandOut])
async def get_value_bands(db: AsyncSession = Depends(get_session)):
    return await list_value_bands(db)


@router.get("/{code}", response_model=ValueBandOut)
async def get_value_band_by_code(code: str, db: AsyncSession = Depends(get_session)):
    obj = await get_value_band(db, code)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value band not found")
    return obj


@router.patch("/{code}", response_model=ValueBandOut)
async def patch_value_band(code: str, payload: ValueBandUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_value_band(db, code)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value band not found")
    obj = await update_value_band(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_value_band(code: str, db: AsyncSession = Depends(get_session)):
    ok = await delete_value_band(db, code)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value band not found")
    await db.commit()
    return None
