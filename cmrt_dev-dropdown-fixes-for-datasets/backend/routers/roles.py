from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.roles import RoleOut, RoleCreate, RoleUpdate
from crud.roles import create_role, get_role, get_role_by_name, list_roles, update_role, delete_role

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_new_role(payload: RoleCreate, db: AsyncSession = Depends(get_session)):
    existing = await get_role_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    obj = await create_role(db, payload)
    await db.commit()
    return obj


@router.get("", response_model=List[RoleOut])
async def get_roles(skip: int = 0, limit: int = 50, is_active: Optional[bool] = None, db: AsyncSession = Depends(get_session)):
    objs = await list_roles(db, skip, limit, is_active)
    return objs


@router.get("/{role_id:uuid}", response_model=RoleOut)
async def get_role_by_id(role_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_role(db, role_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return obj


@router.patch("/{role_id:uuid}", response_model=RoleOut)
async def patch_role(role_id: UUID, payload: RoleUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_role(db, role_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if payload.name:
        existing = await get_role_by_name(db, payload.name)
        if existing and existing.id != role_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    obj = await update_role(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{role_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(role_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_role(db, role_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await db.commit()
    return None
