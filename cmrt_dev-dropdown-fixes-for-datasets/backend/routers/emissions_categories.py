from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.emissions_categories import (
    EmissionsCategoryCreate,
    EmissionsCategoryOut,
    EmissionsCategoryUpdate,
)
from crud.emissions_categories import (
    create_emissions_category,
    get_emissions_category,
    list_emissions_categories,
    list_emissions_categories_by_parent,
    update_emissions_category,
    delete_emissions_category,
)

router = APIRouter(prefix="/api/emissions-categories", tags=["emissions-categories"])


@router.post("", response_model=EmissionsCategoryOut, status_code=status.HTTP_201_CREATED)
async def create_new_emissions_category(
    payload: EmissionsCategoryCreate, db: AsyncSession = Depends(get_session)
):
    obj = await create_emissions_category(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[EmissionsCategoryOut])
async def get_emissions_categories(
    is_active: Optional[bool] = None,
    scope: Optional[int] = None,
    parent_category_id: Optional[UUID] = None,
    top_level_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    if top_level_only:
        return await list_emissions_categories_by_parent(db, parent_category_id=None, skip=skip, limit=limit)
    if parent_category_id is not None:
        return await list_emissions_categories_by_parent(db, parent_category_id, skip, limit)
    return await list_emissions_categories(db, is_active, scope, skip, limit)


@router.get("/{category_id}", response_model=EmissionsCategoryOut)
async def get_emissions_category_by_id(category_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_emissions_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emissions category not found")
    return obj


@router.get("/{category_id}/children", response_model=List[EmissionsCategoryOut])
async def get_child_emissions_categories(
    category_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_emissions_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emissions category not found")
    return await list_emissions_categories_by_parent(db, category_id, skip, limit)


@router.patch("/{category_id}", response_model=EmissionsCategoryOut)
async def patch_emissions_category(
    category_id: UUID, payload: EmissionsCategoryUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_emissions_category(db, category_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emissions category not found")
    obj = await update_emissions_category(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_emissions_category(category_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_emissions_category(db, category_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emissions category not found")
    await db.commit()
    return None
