from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from models.project_type import ProjectType, ProjectTypecast
from schemas.project_type import (
    ProjectTypeCreate, ProjectTypeUpdate,
    ProjectTypecastCreate, ProjectTypecastUpdate
)

# -------- ProjectType
async def create_type(db: AsyncSession, payload: ProjectTypeCreate) -> ProjectType:
    exists = (await db.execute(
        select(ProjectType).where(ProjectType.name.ilike(payload.name.strip()))
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project type name already exists")
    obj = ProjectType(name=payload.name.strip(), is_active=payload.is_active)
    db.add(obj)
    await db.flush(); await db.refresh(obj)
    return obj

async def get_type(db: AsyncSession, project_type_id: UUID) -> Optional[ProjectType]:
    return (await db.execute(
        select(ProjectType).where(ProjectType.id == project_type_id)
    )).scalar_one_or_none()

async def list_types(db: AsyncSession, is_active: Optional[bool], skip: int, limit: int) -> List[ProjectType]:
    q = select(ProjectType)
    if is_active is not None:
        q = q.where(ProjectType.is_active == is_active)
    q = q.order_by(ProjectType.name).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()

async def update_type(db: AsyncSession, obj: ProjectType, payload: ProjectTypeUpdate) -> ProjectType:
    data = payload.dict(exclude_unset=True)
    if "name" in data and data["name"]:
        exists = (await db.execute(
            select(ProjectType).where(ProjectType.name.ilike(data["name"].strip()))
        )).scalar_one_or_none()
        if exists and exists.id != obj.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project type name already exists")
        obj.name = data["name"].strip()
    if "is_active" in data and data["is_active"] is not None:
        obj.is_active = data["is_active"]
    await db.flush(); await db.refresh(obj)
    return obj

async def delete_type(db: AsyncSession, project_type_id: UUID) -> bool:
    obj = await get_type(db, project_type_id)
    if not obj:
        return False
    await db.delete(obj)
    return True

# -------- ProjectTypecast
async def create_typecast(db: AsyncSession, payload: ProjectTypecastCreate) -> ProjectTypecast:
    # uniqueness per (project_type_id, name)
    exists = (await db.execute(
        select(ProjectTypecast).where(
            (ProjectTypecast.project_type_id == payload.project_type_id) &
            (ProjectTypecast.name.ilike(payload.name.strip()))
        )
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Typecast already exists for this type")

    obj = ProjectTypecast(
        project_type_id=payload.project_type_id,
        name=payload.name.strip(),
        is_maintenance=payload.is_maintenance,
        is_active=payload.is_active
    )
    db.add(obj)
    await db.flush(); await db.refresh(obj)
    return obj

async def get_typecast(db: AsyncSession, project_typecast_id: UUID) -> Optional[ProjectTypecast]:
    return (await db.execute(
        select(ProjectTypecast).where(ProjectTypecast.id == project_typecast_id)
    )).scalar_one_or_none()

async def list_typecasts(
    db: AsyncSession,
    project_type_id: Optional[UUID],
    is_active: Optional[bool],
    only_maintenance: Optional[bool],
    skip: int, limit: int
) -> List[ProjectTypecast]:
    q = select(ProjectTypecast)
    if project_type_id:
        q = q.where(ProjectTypecast.project_type_id == project_type_id)
    if is_active is not None:
        q = q.where(ProjectTypecast.is_active == is_active)
    if only_maintenance is not None:
        q = q.where(ProjectTypecast.is_maintenance == only_maintenance)
    q = q.order_by(ProjectTypecast.name).offset(skip).limit(limit)
    return (await db.execute(q)).scalars().all()

async def update_typecast(db: AsyncSession, obj: ProjectTypecast, payload: ProjectTypecastUpdate) -> ProjectTypecast:
    data = payload.dict(exclude_unset=True)
    if "name" in data and data["name"]:
        # check uniqueness within same type
        exists = (await db.execute(
            select(ProjectTypecast).where(
                (ProjectTypecast.project_type_id == obj.project_type_id) &
                (ProjectTypecast.name.ilike(data["name"].strip()))
            )
        )).scalar_one_or_none()
        if exists and exists.id != obj.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Typecast already exists for this type")
        obj.name = data["name"].strip()
    if "is_maintenance" in data and data["is_maintenance"] is not None:
        obj.is_maintenance = data["is_maintenance"]
    if "is_active" in data and data["is_active"] is not None:
        obj.is_active = data["is_active"]
    await db.flush(); await db.refresh(obj)
    return obj

async def delete_typecast(db: AsyncSession, project_typecast_id: UUID) -> bool:
    obj = await get_typecast(db, project_typecast_id)
    if not obj:
        return False
    await db.delete(obj)
    return True