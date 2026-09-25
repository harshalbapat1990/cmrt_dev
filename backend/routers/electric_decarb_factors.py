from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from models.electric_decarb_factors import ElectricDecarbFactor
from sqlalchemy import select
from crud.electric_decarb_factors import (
    list_electric_decarb_factors,
    update_electric_decarb_factor,
    create_decarb_series,
)
from schemas.electric_decarb_factors import (
    ElectricDecarbFactorOut,
    ElectricDecarbFactorUpdate,
    DecarbBulkCreate,
)

router = APIRouter(prefix="/api/electric-decarb-factors", tags=["electric-decarb-factors"])


@router.get("", response_model=List[ElectricDecarbFactorOut])
async def get_electric_decarb_factors(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    jurisdiction_id: Optional[UUID] = Query(None, description="Filter by jurisdiction"),
    factor_type_code: Optional[str] = Query(None, description="Filter by factor type code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=10000),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_electric_decarb_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        factor_type_code=factor_type_code,
        skip=skip,
        limit=limit,
    )
    return rows


@router.put("/{factor_id}", response_model=ElectricDecarbFactorOut)
async def update_decarb_factor(
    factor_id: UUID,
    body: ElectricDecarbFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(ElectricDecarbFactor.dataset_revision_id).where(ElectricDecarbFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="electric_decarb_factors",
    )

    try:
        result = await update_electric_decarb_factor(
            db, factor_id, body.value, body.value_qualifier
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Factor not found")
    return result


@router.post("/bulk", response_model=List[ElectricDecarbFactorOut])
async def bulk_create_decarb_series(
    body: DecarbBulkCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=body.dataset_revision_id,
        dataset_type="electric_decarb_factors",
    )

    try:
        result = await create_decarb_series(
            db,
            dataset_revision_id=body.dataset_revision_id,
            factor_type_code=body.factor_type_code,
            jurisdiction_id=body.jurisdiction_id,
            region_id=body.region_id,
            year_from=body.year_from,
            year_to=body.year_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result
