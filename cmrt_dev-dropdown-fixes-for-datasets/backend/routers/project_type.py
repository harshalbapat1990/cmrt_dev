# backend/routers/project_type.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.session import get_session

from schemas.project_type import (
    ProjectTypeOut, ProjectTypeCreate, ProjectTypeUpdate,
    ProjectTypecastOut, ProjectTypecastCreate, ProjectTypecastUpdate
)
from crud.project_type import (
    create_type, get_type, list_types, update_type, delete_type,
    create_typecast, get_typecast, list_typecasts, update_typecast, delete_typecast
)

router = APIRouter(prefix="/api/project-types", tags=["project-types"])

# ---- types
@router.post("", response_model=ProjectTypeOut, status_code=status.HTTP_201_CREATED)
async def create_project_type(payload: ProjectTypeCreate, db: AsyncSession = Depends(get_session)):
    obj = await create_type(db, payload); await db.commit(); return obj

@router.get("/get-project-types", response_model=List[ProjectTypeOut])
async def get_project_types(
    is_active: Optional[bool] = None, skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_session)
):
    return await list_types(db, is_active, skip, limit)

@router.get("/typecasts", response_model=List[ProjectTypecastOut])
async def get_project_typecasts(
    project_type_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    only_maintenance: Optional[bool] = Query(None, description="Filter maintenance-oriented typecasts"),
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_session)
):
    return await list_typecasts(db, project_type_id, is_active, only_maintenance, skip, limit)

@router.get("/typecasts/{id:uuid}", response_model=ProjectTypecastOut)
async def get_one_typecast(id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_typecast(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project typecast not found")
    return obj

@router.patch("/typecasts/{id:uuid}", response_model=ProjectTypecastOut)
async def patch_project_typecast(id: UUID, payload: ProjectTypecastUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_typecast(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project typecast not found")
    obj = await update_typecast(db, obj, payload); await db.commit(); return obj

@router.delete("/typecasts/{id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_typecast(id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_typecast(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project typecast not found")
    await db.commit(); return None

@router.get("/{id:uuid}", response_model=ProjectTypeOut)
async def get_project_type(id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_type(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project type not found")
    return obj

@router.patch("/{id:uuid}", response_model=ProjectTypeOut)
async def patch_project_type(id: UUID, payload: ProjectTypeUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_type(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project type not found")
    obj = await update_type(db, obj, payload); await db.commit(); return obj

@router.delete("/{id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_type(id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_type(db, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project type not found")
    await db.commit(); return None

# ---- typecasts
@router.post("/{id:uuid}/typecasts", response_model=ProjectTypecastOut, status_code=status.HTTP_201_CREATED)
async def create_project_typecast(
    id: UUID, payload: ProjectTypecastCreate, db: AsyncSession = Depends(get_session)
):
    # ensure path id == body id for clarity
    payload.project_type_id = id
    obj = await create_typecast(db, payload); await db.commit(); return obj

