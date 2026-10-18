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
from schemas.benchmark_mastertypes import BenchmarkMastertypeOut
from crud.benchmark_mastertypes import list_benchmark_mastertypes, get_benchmark_mastertype
from crud.project import get_jurisdiction_name_for_project

router = APIRouter(prefix="/api/benchmark-mastertypes", tags=["benchmark-mastertypes"])


@router.get("", response_model=List[BenchmarkMastertypeOut])
async def get_benchmark_mastertypes(
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
    items = await list_benchmark_mastertypes(
        db, jurisdiction_name=jurisdiction_name, dataset_revision_id=dataset_revision_id
    )
    return [BenchmarkMastertypeOut.model_validate(i) for i in items]


@router.get("/{mastertype_id}", response_model=BenchmarkMastertypeOut)
async def get_benchmark_mastertype_by_id(
    mastertype_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    item = await get_benchmark_mastertype(db, mastertype_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark mastertype not found")
    return BenchmarkMastertypeOut.model_validate(item)
