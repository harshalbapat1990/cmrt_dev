from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from schemas.permissions import PermissionOut
from crud.permissions import list_permissions, get_permission

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("", response_model=List[PermissionOut])
async def get_permissions(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    """
    Get all permissions with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Number of records to return (default: 50, max: 500)
    """
    permissions = await list_permissions(db, skip, limit)
    return permissions


@router.get("/{permission_id}", response_model=PermissionOut)
async def get_permission_by_id(
    permission_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a single permission by ID.
    
    - **permission_id**: UUID of the permission
    """
    permission = await get_permission(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return permission