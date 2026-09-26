from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.base_case_assumptions import (
    BaseCaseAssumptionCreate,
    BaseCaseAssumptionOut,
    BaseCaseAssumptionUpdate,
)
from crud.base_case_assumptions import (
    create_base_case_assumption,
    get_base_case_assumption,
    get_base_case_assumption_by_category_name,
    list_base_case_assumptions,
    update_base_case_assumption,
    delete_base_case_assumption,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/base-case-assumptions", tags=["base-case-assumptions"])


@router.post("", response_model=BaseCaseAssumptionOut, status_code=status.HTTP_201_CREATED)
async def create_new_base_case_assumption(
    payload: BaseCaseAssumptionCreate, db: AsyncSession = Depends(get_session)
):
    existing = await get_base_case_assumption_by_category_name(db, payload.emissions_category_id, payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assumption with this category and name already exists",
        )
    obj = await create_base_case_assumption(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[BaseCaseAssumptionOut])
async def get_base_case_assumptions(
    emissions_category_id: Optional[UUID] = None,
    is_anz_default: Optional[bool] = None,
    dataset_revision_id: Optional[UUID] = Query(
        None, description="Filter to assumptions belonging to a specific dataset revision"
    ),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_base_case_assumptions(db, emissions_category_id, is_anz_default, dataset_revision_id, skip, limit)


@router.get("/{assumption_id}", response_model=BaseCaseAssumptionOut)
async def get_base_case_assumption_by_id(assumption_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_base_case_assumption(db, assumption_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
    return obj


@router.patch("/{assumption_id}", response_model=BaseCaseAssumptionOut)
async def patch_base_case_assumption(
    assumption_id: UUID, payload: BaseCaseAssumptionUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_base_case_assumption(db, assumption_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
    obj = await update_base_case_assumption(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{assumption_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_base_case_assumption(assumption_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_base_case_assumption(db, assumption_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assumption not found")
    await db.commit()
    return None

protect_dataset_reads(router)
