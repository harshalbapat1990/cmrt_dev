from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from models.ev_uptake_factors import EvUptakeFactor
from sqlalchemy import select
from crud.ev_uptake_factors import (
    list_ev_uptake_factors,
    update_ev_uptake_factor,
    create_ev_uptake_series,
)
from schemas.ev_uptake_factors import (
    EvUptakeFactorOut,
    EvUptakeFactorUpdate,
    EvUptakeBulkCreate,
)

router = APIRouter(prefix="/api/ev-uptake-factors", tags=["ev-uptake-factors"])


@router.get("", response_model=List[EvUptakeFactorOut])
async def get_ev_uptake_factors(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    jurisdiction_id: Optional[UUID] = Query(None, description="Filter by jurisdiction"),
    scenario_code: Optional[str] = Query(None, description="Filter by scenario code"),
    vehicle_category_code: Optional[str] = Query(None, description="Filter by vehicle category code"),
    energy_type_code: Optional[str] = Query(None, description="Filter by energy type code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=100000),
    db: AsyncSession = Depends(get_session),
):
    return await list_ev_uptake_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        scenario_code=scenario_code,
        vehicle_category_code=vehicle_category_code,
        energy_type_code=energy_type_code,
        skip=skip,
        limit=limit,
    )


@router.put("/{factor_id}", response_model=EvUptakeFactorOut)
async def update_ev_uptake(
    factor_id: UUID,
    body: EvUptakeFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(EvUptakeFactor.dataset_revision_id).where(EvUptakeFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="ev_uptake_factors",
    )

    try:
        result = await update_ev_uptake_factor(db, factor_id, body.uptake_pct)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Factor not found")
    return result


@router.post("/bulk", response_model=List[EvUptakeFactorOut], status_code=status.HTTP_201_CREATED)
async def bulk_create_ev_uptake_series(
    body: EvUptakeBulkCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=body.dataset_revision_id,
        dataset_type="ev_uptake_factors",
    )

    try:
        result = await create_ev_uptake_series(
            db,
            dataset_revision_id=body.dataset_revision_id,
            jurisdiction_id=body.jurisdiction_id,
            scenario_code=body.scenario_code,
            vehicle_category_code=body.vehicle_category_code,
            energy_type_code=body.energy_type_code,
            year_from=body.year_from,
            year_to=body.year_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result
