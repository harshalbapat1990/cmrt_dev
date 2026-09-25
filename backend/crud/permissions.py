from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.permissions import Permission
from schemas.permissions import PermissionOut


async def list_permissions(db: AsyncSession, skip: int = 0, limit: int = 50) -> List[Permission]:
    """List all permissions with pagination"""
    query = select(Permission).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_permission(db: AsyncSession, permission_id: UUID) -> Optional[Permission]:
    """Get a single permission by ID"""
    query = select(Permission).where(Permission.id == permission_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_permission_by_name(db: AsyncSession, name: str) -> Optional[Permission]:
    """Get a permission by name"""
    query = select(Permission).where(Permission.name == name)
    result = await db.execute(query)
    return result.scalars().first()