from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from models.freight_rail_factors import FreightRailFactor
from sqlalchemy import select
from crud.freight_rail_factors import delete_freight_rail_factor, list_freight_rail_factors, update_freight_rail_factor
from schemas.freight_rail_factors import FreightRailFactorOut, FreightRailFactorUpdate

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/freight-rail-factors", tags=["freight-rail-factors"])


@router.get("", response_model=List[FreightRailFactorOut])
async def get_freight_rail_factors(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
):
    return await list_freight_rail_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        skip=skip,
        limit=limit,
    )


@router.put("/{factor_id}", response_model=FreightRailFactorOut)
async def update_freight_rail(
    factor_id: UUID,
    body: FreightRailFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(FreightRailFactor.dataset_revision_id).where(FreightRailFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="freight_rail_factors",
    )

    try:
        result = await update_freight_rail_factor(
            db,
            factor_id,
            body.fuel_consumption_l_per_000_gtk,
            body.source_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Factor not found")
    return result


@router.delete("/{factor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_freight_rail(
    factor_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(FreightRailFactor.dataset_revision_id).where(FreightRailFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="freight_rail_factors",
    )

    try:
        ok = await delete_freight_rail_factor(db, factor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Factor not found")
    await db.commit()
    return None

protect_dataset_reads(router)
