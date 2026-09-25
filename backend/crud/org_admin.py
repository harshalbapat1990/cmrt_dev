from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from models.user_roles import UserRole
from models.roles import Role
from models.project import Project
from models.project_organizations import ProjectOrganization


async def get_org_users_with_project_roles(
    db: AsyncSession,
    organization_id: UUID,
    include_inactive: bool = False
) -> List[dict]:
    user_query = select(User).where(User.organization_id == organization_id)
    
    if not include_inactive:
        user_query = user_query.where(User.is_active == True)
    
    user_result = await db.execute(user_query)
    users = user_result.scalars().all()
    
    result = []
    
    for user in users:
        proponent_projects_q = select(Project.id, Project.project_name).where(
            Project.proponent_org_id == organization_id
        )
        proponent_result = await db.execute(proponent_projects_q)
        proponent_projects = {p.id: p.project_name for p in proponent_result.all()}
        
        secondary_projects_q = select(
            ProjectOrganization.project_id,
            Project.project_name
        ).join(
            Project, Project.id == ProjectOrganization.project_id
        ).where(
            ProjectOrganization.organization_id == organization_id
        )
        secondary_result = await db.execute(secondary_projects_q)
        secondary_projects = {p.project_id: p.project_name for p in secondary_result.all()}
        
        all_org_project_ids = set(list(proponent_projects.keys()) + list(secondary_projects.keys()))
        all_project_names = {**proponent_projects, **secondary_projects}
        
        if all_org_project_ids:
            role_query = (
                select(
                    UserRole.id.label('user_role_id'),
                    UserRole.scope_id.label('project_id'),
                    UserRole.is_active,
                    Role.name.label('role_name')
                )
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    and_(
                        UserRole.user_id == user.id,
                        UserRole.scope_type == 'PROJECT',
                        UserRole.scope_id.in_(all_org_project_ids)
                    )
                )
            )
            role_result = await db.execute(role_query)
            user_project_roles = role_result.all()
        else:
            user_project_roles = []
        
        org_admin_query = (
            select(UserRole.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                and_(
                    UserRole.user_id == user.id,
                    UserRole.scope_type == 'ORGANISATION',
                    UserRole.scope_id == organization_id,
                    Role.name == 'ORG_ADMIN',
                    UserRole.is_active == True
                )
            )
        )
        org_admin_result = await db.execute(org_admin_query)
        org_admin_user_role_id = org_admin_result.scalar()
        has_org_admin_role = org_admin_user_role_id is not None
        
        project_roles = []
        for role_row in user_project_roles:
            project_id = role_row.project_id
            project_roles.append({
                'project_id': str(project_id),
                'project_name': all_project_names.get(project_id, 'Unknown'),
                'role_name': role_row.role_name,
                'user_role_id': str(role_row.user_role_id),
                'is_active': role_row.is_active
            })
        
        display_name = None
        if user.first_name or user.last_name:
            display_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        
        result.append({
            'user_id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'display_name': display_name,
            'is_active': user.is_active,
            'project_roles': project_roles,
            'has_org_admin_role': has_org_admin_role,
            'org_admin_user_role_id': str(org_admin_user_role_id) if org_admin_user_role_id else None,
        })
    
    return result


async def verify_project_belongs_to_org(
    db: AsyncSession,
    project_id: UUID,
    organization_id: UUID
) -> bool:
    proponent_query = select(Project.id).where(
        and_(
            Project.id == project_id,
            Project.proponent_org_id == organization_id
        )
    )
    proponent_result = await db.execute(proponent_query)
    if proponent_result.scalar() is not None:
        return True
    
    secondary_query = select(ProjectOrganization.project_id).where(
        and_(
            ProjectOrganization.project_id == project_id,
            ProjectOrganization.organization_id == organization_id
        )
    )
    secondary_result = await db.execute(secondary_query)
    return secondary_result.scalar() is not None


async def verify_user_in_org(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID
) -> bool:
    query = select(User.id).where(
        and_(
            User.id == user_id,
            User.organization_id == organization_id
        )
    )
    result = await db.execute(query)
    return result.scalar() is not None


async def get_user_project_admin_role(
    db: AsyncSession,
    user_id: UUID,
    project_id: UUID
) -> Optional[UUID]:
    query = (
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            and_(
                UserRole.user_id == user_id,
                UserRole.scope_type == 'PROJECT',
                UserRole.scope_id == project_id,
                Role.name == 'PROJECT_ADMIN'
            )
        )
    )
    result = await db.execute(query)
    return result.scalar()
