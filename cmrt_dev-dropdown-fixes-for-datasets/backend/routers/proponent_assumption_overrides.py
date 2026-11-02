from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.proponent_assumption_overrides import (
    ProponentAssumptionOverrideCreate,
    ProponentAssumptionOverrideOut,
    ProponentAssumptionOverrideUpdate,
)
from crud.proponent_assumption_overrides import (
    create_proponent_assumption_override,
    get_proponent_assumption_override,
    get_proponent_assumption_override_by_key,
    list_proponent_assumption_overrides,
    update_proponent_assumption_override,
    delete_proponent_assumption_override,
)

router = APIRouter(prefix="/api/proponent-assumption-overrides", tags=["proponent-assumption-overrides"])


@router.post("", response_model=ProponentAssumptionOverrideOut, status_code=status.HTTP_201_CREATED)
async def create_new_override(
    payload: ProponentAssumptionOverrideCreate, db: AsyncSession = Depends(get_session)
):
    existing = await get_proponent_assumption_override_by_key(
        db, payload.proponent_org_id, payload.assumption_id, payload.effective_from
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Override for this org, assumption, and effective_from already exists",
        )
    obj = await create_proponent_assumption_override(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[ProponentAssumptionOverrideOut])
async def get_overrides(
    proponent_org_id: Optional[UUID] = None,
    assumption_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
):
    return await list_proponent_assumption_overrides(db, proponent_org_id, assumption_id, skip, limit)


@router.get("/{override_id}", response_model=ProponentAssumptionOverrideOut)
async def get_override_by_id(override_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_proponent_assumption_override(db, override_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    return obj


@router.patch("/{override_id}", response_model=ProponentAssumptionOverrideOut)
async def patch_override(
    override_id: UUID, payload: ProponentAssumptionOverrideUpdate, db: AsyncSession = Depends(get_session)
):
    obj = await get_proponent_assumption_override(db, override_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    obj = await update_proponent_assumption_override(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_override(override_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_proponent_assumption_override(db, override_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    await db.commit()
    return None
