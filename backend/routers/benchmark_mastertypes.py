from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.benchmark_mastertypes import BenchmarkMastertypeOut
from crud.benchmark_mastertypes import list_benchmark_mastertypes, get_benchmark_mastertype
from crud.project import get_jurisdiction_name_for_project

router = APIRouter(prefix="/api/benchmark-mastertypes", tags=["benchmark-mastertypes"])


@router.get("", response_model=List[BenchmarkMastertypeOut])
async def get_benchmark_mastertypes(
    project_id: Optional[UUID] = Query(None, description="Filter by the project's jurisdiction"),
    db: AsyncSession = Depends(get_session),
):
    jurisdiction_name: Optional[str] = None
    if project_id:
        jurisdiction_name = await get_jurisdiction_name_for_project(db, project_id)
    items = await list_benchmark_mastertypes(db, jurisdiction_name=jurisdiction_name)
    return [BenchmarkMastertypeOut.model_validate(i) for i in items]


@router.get("/{mastertype_id}", response_model=BenchmarkMastertypeOut)
async def get_benchmark_mastertype_by_id(mastertype_id: UUID, db: AsyncSession = Depends(get_session)):
    item = await get_benchmark_mastertype(db, mastertype_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark mastertype not found")
    return BenchmarkMastertypeOut.model_validate(item)
