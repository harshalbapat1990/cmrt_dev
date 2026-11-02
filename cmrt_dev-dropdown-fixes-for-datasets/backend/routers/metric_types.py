from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.metric_types import MetricTypeCreate, MetricTypeOut, MetricTypeUpdate
from crud.metric_types import (
    create_metric_type,
    get_metric_type,
    get_metric_type_by_code,
    list_metric_types,
    update_metric_type,
    delete_metric_type,
)

router = APIRouter(prefix="/api/metric-types", tags=["metric-types"])


@router.post("", response_model=MetricTypeOut, status_code=status.HTTP_201_CREATED)
async def create_new_metric_type(payload: MetricTypeCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_metric_type_by_code(db, payload.code)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Metric type code already exists")
    obj = await create_metric_type(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[MetricTypeOut])
async def get_metric_types(db: AsyncSession = Depends(get_session)):
    return await list_metric_types(db)


@router.get("/by-code/{code}", response_model=MetricTypeOut)
async def get_metric_type_endpoint_by_code(code: str, db: AsyncSession = Depends(get_session)):
    obj = await get_metric_type_by_code(db, code)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric type not found")
    return obj


@router.get("/{metric_type_id}", response_model=MetricTypeOut)
async def get_metric_type_by_id(metric_type_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_metric_type(db, metric_type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric type not found")
    return obj


@router.patch("/{metric_type_id}", response_model=MetricTypeOut)
async def patch_metric_type(metric_type_id: UUID, payload: MetricTypeUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_metric_type(db, metric_type_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric type not found")
    obj = await update_metric_type(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{metric_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_metric_type(metric_type_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_metric_type(db, metric_type_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric type not found")
    await db.commit()
    return None
