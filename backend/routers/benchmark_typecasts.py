from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import Principal, get_current_principal
from core.dataset_authorization import (
    assert_dataset_revision_read_permission,
    assert_project_dataset_revision_read_permission,
)
from schemas.benchmark_typecasts import BenchmarkTypecastOut
from crud.benchmark_typecasts import list_benchmark_typecasts, get_benchmark_typecast
from crud.project import get_jurisdiction_name_for_project

router = APIRouter(prefix="/api/benchmark-typecasts", tags=["benchmark-typecasts"])


@router.get("", response_model=List[BenchmarkTypecastOut])
async def get_benchmark_typecasts(
    mastertype_id: Optional[UUID] = Query(None, description="Filter by mastertype"),
    project_id: Optional[UUID] = Query(None, description="Filter by the project's jurisdiction"),
    dataset_revision_id: Optional[UUID] = Query(None),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    if project_id is not None:
        dataset_revision_id = await assert_project_dataset_revision_read_permission(
            db, principal, project_id, dataset_revision_id
        )
    elif dataset_revision_id is not None:
        await assert_dataset_revision_read_permission(db, principal, dataset_revision_id)
    jurisdiction_name: Optional[str] = None
    if project_id:
        jurisdiction_name = await get_jurisdiction_name_for_project(db, project_id)
    items = await list_benchmark_typecasts(
        db,
        mastertype_id=mastertype_id,
        jurisdiction_name=jurisdiction_name,
        dataset_revision_id=dataset_revision_id,
    )
    return [BenchmarkTypecastOut.model_validate(i) for i in items]


@router.get("/{typecast_id}", response_model=BenchmarkTypecastOut)
async def get_benchmark_typecast_by_id(
    typecast_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    item = await get_benchmark_typecast(db, typecast_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark typecast not found")
    return BenchmarkTypecastOut.model_validate(item)
