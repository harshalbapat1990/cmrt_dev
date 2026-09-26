from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from models.vepm_factors import VepmFactor
from sqlalchemy import select
from crud.vepm_factors import delete_vepm_factor, list_vepm_factors, update_vepm_factor
from schemas.vepm_factors import VepmFactorOut, VepmFactorUpdate

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/vepm-factors", tags=["vepm-factors"])


@router.get("", response_model=List[VepmFactorOut])
async def get_vepm_factors(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    year: Optional[int] = Query(None, description="Filter by year"),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=10000),
    db: AsyncSession = Depends(get_session),
):
    return await list_vepm_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        year=year,
        skip=skip,
        limit=limit,
    )


@router.put("/{factor_id}", response_model=VepmFactorOut)
async def update_vepm(
    factor_id: UUID,
    body: VepmFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(VepmFactor.dataset_revision_id).where(VepmFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="vepm_factors",
    )

    try:
        result = await update_vepm_factor(
            db,
            factor_id,
            body.fleet_average_co2e_g_km,
            body.light_vehicle_co2e_g_km,
            body.heavy_vehicle_co2e_g_km,
            body.bus_co2e_g_km,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Factor not found")
    return result


@router.delete("/{factor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vepm(
    factor_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(VepmFactor.dataset_revision_id).where(VepmFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="vepm_factors",
    )

    try:
        ok = await delete_vepm_factor(db, factor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Factor not found")
    await db.commit()
    return None

protect_dataset_reads(router)
