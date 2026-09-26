from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from crud.carbon_values import (
    list_carbon_values,
    update_carbon_value,
    create_carbon_value_series,
)
from schemas.carbon_values import (
    CarbonValueOut,
    CarbonValueUpdate,
    CarbonValueBulkCreate,
)

from core.security import get_current_principal, Principal
from core.dataset_authorization import (
    assert_revision_edit_permission,
)

from models.carbon_values import CarbonValue
from sqlalchemy import select

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/carbon-values", tags=["carbon-values"])


@router.get("", response_model=List[CarbonValueOut])
async def get_carbon_values(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    jurisdiction_id: Optional[UUID] = Query(None, description="Filter by jurisdiction"),
    range_code: Optional[str] = Query(None, description="Filter by range code (low/central/high)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=10000),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_carbon_values(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        range_code=range_code,
        skip=skip,
        limit=limit,
    )
    return rows


@router.put("/{value_id}", response_model=CarbonValueOut)
async def update_carbon_value_endpoint(
    value_id: UUID,
    body: CarbonValueUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(CarbonValue.dataset_revision_id)
        .where(CarbonValue.id == value_id)
    )

    revision_id = res.scalar_one_or_none()

    if revision_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carbon value not found",
        )

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="carbon_values",
    )

    try:
        result = await update_carbon_value(
            db, value_id, body.value, body.currency, body.source
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Carbon value not found")
    return result


@router.post("/bulk", response_model=List[CarbonValueOut], status_code=status.HTTP_201_CREATED)
async def bulk_create_carbon_value_series(
    body: CarbonValueBulkCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=body.dataset_revision_id,
        dataset_type="carbon_values",
    )

    try:
        result = await create_carbon_value_series(
            db,
            dataset_revision_id=body.dataset_revision_id,
            jurisdiction_id=body.jurisdiction_id,
            range_code=body.range_code,
            year_from=body.year_from,
            year_to=body.year_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result

protect_dataset_reads(router)
