from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.role_permissions import RolePermissionOut, RolePermissionCreate
from crud.role_permissions import (
    create_role_permission,
    list_role_permissions,
    get_role_permission,
    delete_role_permission
)

router = APIRouter(prefix="/api/role-permissions", tags=["role-permissions"])


@router.post("", response_model=RolePermissionOut, status_code=status.HTTP_201_CREATED)
async def create_new_role_permission(
    payload: RolePermissionCreate,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new role-permission mapping.
    
    Both role_id and permission_id must exist and the combination must be unique.
    """
    role_permission = await create_role_permission(db, payload.role_id, payload.permission_id)
    await db.commit()
    return role_permission


@router.get("", response_model=List[RolePermissionOut])
async def get_role_permissions(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    role_id: Optional[UUID] = Query(None, description="Filter by role ID"),
    permission_id: Optional[UUID] = Query(None, description="Filter by permission ID"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all role-permissions with optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Number of records to return (default: 50, max: 500)
    - **role_id**: Optional UUID to filter by specific role
    - **permission_id**: Optional UUID to filter by specific permission
    """
    role_permissions = await list_role_permissions(
        db, skip, limit, role_id, permission_id
    )
    return role_permissions


@router.get("/{role_permission_id}", response_model=RolePermissionOut)
async def get_role_permission_by_id(
    role_permission_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a single role-permission mapping by ID.
    
    - **role_permission_id**: UUID of the role-permission mapping
    """
    role_permission = await get_role_permission(db, role_permission_id)
    if not role_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role-Permission mapping not found"
        )
    return role_permission


@router.delete("/{role_permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_permission(
    role_permission_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete a role-permission mapping by ID.
    
    - **role_permission_id**: UUID of the role-permission mapping to delete
    """
    ok = await delete_role_permission(db, role_permission_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role-Permission mapping not found"
        )
    await db.commit()
    return None