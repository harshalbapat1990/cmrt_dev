from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from models.user_roles import UserRole
from models.users import User
from models.roles import Role


async def create_user_role(
    db: AsyncSession,
    user_id: UUID,
    role_id: UUID,
    scope_type: Optional[str] = None,
    scope_id: Optional[UUID] = None,
    is_active: bool = True
) -> UserRole:
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalars().first():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    if not role_result.scalars().first():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    existing = await db.execute(
        select(UserRole).where(
            and_(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
                UserRole.scope_type == scope_type,
                UserRole.scope_id == scope_id
            )
        )
    )
    if existing.scalars().first():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User-Role mapping already exists"
        )
    
    user_role = UserRole(
        user_id=user_id,
        role_id=role_id,
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=is_active
    )
    db.add(user_role)
    await db.flush()
    await db.refresh(user_role)
    return user_role


async def list_user_roles(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[UUID] = None,
    role_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[UUID] = None,
) -> List[UserRole]:

    query = select(UserRole)

    if user_id:
        query = query.where(UserRole.user_id == user_id)

    if role_id:
        query = query.where(UserRole.role_id == role_id)

    if is_active is not None:
        query = query.where(UserRole.is_active == is_active)

    if scope_type is not None:
        query = query.where(UserRole.scope_type == scope_type)

    if scope_id is not None:
        query = query.where(UserRole.scope_id == scope_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_user_role(
    db: AsyncSession, user_role_id: UUID
) -> Optional[UserRole]:
    query = select(UserRole).where(UserRole.id == user_role_id)
    result = await db.execute(query)
    return result.scalars().first()


async def update_user_role(
    db: AsyncSession,
    user_role_id: UUID,
    is_active: Optional[bool] = None
) -> Optional[UserRole]:
    user_role = await get_user_role(db, user_role_id)
    if not user_role:
        return None
    
    if is_active is not None:
        user_role.is_active = is_active
    
    await db.flush()
    await db.refresh(user_role)
    return user_role


async def delete_user_role(db: AsyncSession, user_role_id: UUID) -> bool:
    user_role = await get_user_role(db, user_role_id)
    if user_role:
        await db.delete(user_role)
        return True
    return False


async def delete_all_user_roles_for_user(db: AsyncSession, user_id: UUID) -> int:
    roles = await list_user_roles(db, user_id=user_id, limit=10000)
    for role in roles:
        await db.delete(role)
    await db.flush()
    return len(roles)


async def list_user_roles_enriched(
    db: AsyncSession,
    *,
    role_name: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_ids: Optional[List[UUID]] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 200,
) -> List[Dict[str, Any]]:

    from models.organizations import Organization
    from models.project import Project

    display_name = func.nullif(
        func.trim(
            func.coalesce(User.first_name, "") + " " + func.coalesce(User.last_name, "")
        ),
        "",
    ).label("user_display_name")

    query = (
        select(
            UserRole.id.label("user_role_id"),
            UserRole.user_id,
            UserRole.scope_type,
            UserRole.scope_id,
            UserRole.is_active,
            User.email.label("user_email"),
            display_name,
            Role.name.label("role_name"),
            Organization.name.label("org_name"),
            Project.project_name.label("project_name"),
        )
        .join(User, User.id == UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .outerjoin(
            Organization,
            (Organization.id == UserRole.scope_id) & (UserRole.scope_type == "ORGANISATION"),
        )
        .outerjoin(
            Project,
            (Project.id == UserRole.scope_id) & (UserRole.scope_type == "PROJECT"),
        )
    )

    query = query.where(UserRole.is_active == is_active)

    if scope_type:
        query = query.where(UserRole.scope_type == scope_type.upper())
    if role_name:
        query = query.where(Role.name == role_name.upper())
    if scope_ids is not None:
        query = query.where(UserRole.scope_id.in_(scope_ids))

    query = query.order_by(UserRole.scope_id, User.email).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "user_role_id": str(row.user_role_id),
            "user_id": str(row.user_id),
            "user_email": row.user_email,
            "user_display_name": row.user_display_name,
            "role_name": row.role_name,
            "scope_type": row.scope_type,
            "scope_id": str(row.scope_id) if row.scope_id else None,
            "org_name": row.org_name,
            "project_name": row.project_name,
            "is_active": row.is_active,
        }
        for row in rows
    ]