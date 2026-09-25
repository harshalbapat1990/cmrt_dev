from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.benchmark_typecasts import BenchmarkTypecastOut
from crud.benchmark_typecasts import list_benchmark_typecasts, get_benchmark_typecast
from crud.project import get_jurisdiction_name_for_project

router = APIRouter(prefix="/api/benchmark-typecasts", tags=["benchmark-typecasts"])


@router.get("", response_model=List[BenchmarkTypecastOut])
async def get_benchmark_typecasts(
    mastertype_id: Optional[UUID] = Query(None, description="Filter by mastertype"),
    project_id: Optional[UUID] = Query(None, description="Filter by the project's jurisdiction"),
    db: AsyncSession = Depends(get_session),
):
    jurisdiction_name: Optional[str] = None
    if project_id:
        jurisdiction_name = await get_jurisdiction_name_for_project(db, project_id)
    items = await list_benchmark_typecasts(db, mastertype_id=mastertype_id, jurisdiction_name=jurisdiction_name)
    return [BenchmarkTypecastOut.model_validate(i) for i in items]


@router.get("/{typecast_id}", response_model=BenchmarkTypecastOut)
async def get_benchmark_typecast_by_id(typecast_id: UUID, db: AsyncSession = Depends(get_session)):
    item = await get_benchmark_typecast(db, typecast_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark typecast not found")
    return BenchmarkTypecastOut.model_validate(item)
