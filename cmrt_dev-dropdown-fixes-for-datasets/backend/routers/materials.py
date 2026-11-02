from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.materials import MaterialCreate, MaterialOut, MaterialUpdate
from crud.materials import (
    create_material,
    get_material,
    get_material_by_name,
    list_materials,
    update_material,
    delete_material,
)

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.post("", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
async def create_new_material(payload: MaterialCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_material_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material name already exists")
    obj = await create_material(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[MaterialOut])
async def get_materials(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_materials(db, skip, limit, is_active)


@router.get("/{material_id}", response_model=MaterialOut)
async def get_material_by_id(material_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return obj


@router.patch("/{material_id}", response_model=MaterialOut)
async def patch_material(material_id: UUID, payload: MaterialUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    if payload.name:
        existing = await get_material_by_name(db, payload.name)
        if existing and existing.id != material_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material name already exists")
    obj = await update_material(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_material(material_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_material(db, material_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    await db.commit()
    return None
