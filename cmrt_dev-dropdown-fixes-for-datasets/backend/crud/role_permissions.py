from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from fastapi import HTTPException, status

from models.role_permissions import RolePermission
from models.roles import Role
from models.permissions import Permission


async def create_role_permission(
    db: AsyncSession, role_id: UUID, permission_id: UUID
) -> RolePermission:
    """Create a role-permission mapping"""
    # Check if role exists
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    if not role_result.scalars().first():
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if permission exists
    perm_result = await db.execute(select(Permission).where(Permission.id == permission_id))
    if not perm_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Check if mapping already exists
    existing = await db.execute(
        select(RolePermission).where(
            and_(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id
            )
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role-Permission mapping already exists"
        )
    
    role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
    db.add(role_permission)
    await db.flush()
    await db.refresh(role_permission)
    return role_permission


async def list_role_permissions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    role_id: Optional[UUID] = None,
    permission_id: Optional[UUID] = None
) -> List[RolePermission]:
    """List role-permissions with optional filters"""
    query = select(RolePermission)
    
    if role_id:
        query = query.where(RolePermission.role_id == role_id)
    
    if permission_id:
        query = query.where(RolePermission.permission_id == permission_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_role_permission(
    db: AsyncSession, role_permission_id: UUID
) -> Optional[RolePermission]:
    """Get a single role-permission mapping by ID"""
    query = select(RolePermission).where(RolePermission.id == role_permission_id)
    result = await db.execute(query)
    return result.scalars().first()


async def delete_role_permission(db: AsyncSession, role_permission_id: UUID) -> bool:
    """Delete a role-permission mapping"""
    role_permission = await get_role_permission(db, role_permission_id)
    if role_permission:
        await db.delete(role_permission)
        return True
    return False