from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import require_org_admin, SUPER_ADMIN, get_effective_role_names
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.roles import get_role_by_name
from crud.users import get_user, update_user
from crud.user_roles import create_user_role, delete_user_role, delete_all_user_roles_for_user, get_user_role, update_user_role
from models.user_roles import UserRole as UserRoleModel
from models.roles import Role
from schemas.users import UserUpdate
from crud.org_admin import (
    get_org_users_with_project_roles,
    verify_project_belongs_to_org,
    verify_user_in_org,
    get_user_project_admin_role
)
from schemas.org_admin import (
    OrgUserWithRoles,
    AddProjectAdminRequest,
    ProjectAdminResponse,
    AddOrgAdminRequest,
    OrgAdminResponse,
)

router = APIRouter(prefix="/api/org-admin", tags=["org-admin"])


@router.get("/users", response_model=List[OrgUserWithRoles])
async def list_organization_users(
    include_inactive: bool = Query(False, description="Include inactive users"),
    org_id: Optional[UUID] = Query(None, description="Target org (SUPER_ADMIN only)"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    effective_roles = await get_effective_role_names(db, principal.user_id)
    if SUPER_ADMIN in effective_roles:
        if org_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org_id is required for SUPER_ADMIN")
        target_org_id = org_id
    else:
        if not principal.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ORG_ADMIN role required")
        from core.rbac import ORG_ADMIN, get_org_scoped_role_names
        org_roles = await get_org_scoped_role_names(db, principal.user_id, principal.organization_id)
        if ORG_ADMIN not in org_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ORG_ADMIN role required")
        target_org_id = principal.organization_id

    users = await get_org_users_with_project_roles(
        db,
        target_org_id,
        include_inactive=include_inactive
    )
    return users


@router.post("/admins", response_model=OrgAdminResponse, status_code=status.HTTP_201_CREATED)
async def add_org_admin(
    payload: AddOrgAdminRequest,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_org_admin),
    db: AsyncSession = Depends(get_session),
):
    user_in_org = await verify_user_in_org(db, payload.user_id, principal.organization_id)
    if not user_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or does not belong to your organisation",
        )

    org_admin_role = await get_role_by_name(db, "ORG_ADMIN")
    if not org_admin_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ORG_ADMIN role not found in system")

    existing_active = await db.execute(
        select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == payload.user_id,
                UserRoleModel.role_id == org_admin_role.id,
                UserRoleModel.scope_type == "ORGANISATION",
                UserRoleModel.scope_id == principal.organization_id,
                UserRoleModel.is_active == True,
            )
        )
    )
    if existing_active.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already an ORG_ADMIN for this organisation")

    existing_inactive = await db.execute(
        select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == payload.user_id,
                UserRoleModel.role_id == org_admin_role.id,
                UserRoleModel.scope_type == "ORGANISATION",
                UserRoleModel.scope_id == principal.organization_id,
                UserRoleModel.is_active == False,
            )
        )
    )
    inactive_ur = existing_inactive.scalars().first()
    if inactive_ur:
        user_role = await update_user_role(db, inactive_ur.id, is_active=True)
    else:
        user_role = await create_user_role(
            db,
            user_id=payload.user_id,
            role_id=org_admin_role.id,
            scope_type="ORGANISATION",
            scope_id=principal.organization_id,
            is_active=True,
        )

    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role.id,
        action="GRANT_ORG_ADMIN",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(payload.user_id), "role": "ORG_ADMIN", "granted_by_org_admin": True},
    )
    await db.commit()

    return OrgAdminResponse(
        user_id=payload.user_id,
        org_id=principal.organization_id,
        role_name="ORG_ADMIN",
        user_role_id=user_role.id,
        message="Org admin role granted successfully",
    )


@router.delete("/admins/{user_role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_admin(
    user_role_id: UUID,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_org_admin),
    db: AsyncSession = Depends(get_session),
):
    target_ur = await get_user_role(db, user_role_id)
    if not target_ur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role not found")

    org_admin_role = await get_role_by_name(db, "ORG_ADMIN")
    if not org_admin_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ORG_ADMIN role not found in system")
    if (
        str(target_ur.role_id) != str(org_admin_role.id)
        or str(target_ur.scope_type) != "ORGANISATION"
        or str(target_ur.scope_id) != str(principal.organization_id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke this role")

    active_res = await db.execute(
        select(UserRoleModel).where(
            and_(UserRoleModel.id == user_role_id, UserRoleModel.is_active == True)
        )
    )
    if not active_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role not found or already inactive")

    if str(target_ur.user_id) == str(principal.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke your own Org Admin role")

    await update_user_role(db, user_role_id, is_active=False)

    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role_id,
        action="REVOKE_ORG_ADMIN",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(target_ur.user_id), "role": "ORG_ADMIN", "revoked_by_org_admin": True},
    )
    await db.commit()


@router.post("/projects/{project_id}/admins", response_model=ProjectAdminResponse, status_code=status.HTTP_201_CREATED)
async def add_project_admin(
    project_id: UUID,
    payload: AddProjectAdminRequest,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_org_admin),
    db: AsyncSession = Depends(get_session),
):
    project_belongs = await verify_project_belongs_to_org(
        db, project_id, principal.organization_id
    )
    if not project_belongs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or does not belong to your organization"
        )
    
    user_in_org = await verify_user_in_org(
        db, payload.user_id, principal.organization_id
    )
    if not user_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or does not belong to your organization"
        )
    
    existing_role_id = await get_user_project_admin_role(
        db, payload.user_id, project_id
    )
    if existing_role_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has PROJECT_ADMIN role on this project"
        )
    
    project_admin_role = await get_role_by_name(db, "PROJECT_ADMIN")
    if not project_admin_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PROJECT_ADMIN role not found in system"
        )
    
    user_role = await create_user_role(
        db,
        user_id=payload.user_id,
        role_id=project_admin_role.id,
        scope_type="PROJECT",
        scope_id=project_id,
        is_active=True
    )
    
    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role.id,
        action="GRANT_PROJECT_ADMIN",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "target_user_id": str(payload.user_id),
            "project_id": str(project_id),
            "role": "PROJECT_ADMIN",
            "granted_by_org_admin": True
        }
    )
    
    await db.commit()
    
    return ProjectAdminResponse(
        user_id=payload.user_id,
        project_id=project_id,
        role_name="PROJECT_ADMIN",
        user_role_id=user_role.id,
        message="Project admin role granted successfully"
    )


@router.delete("/projects/{project_id}/admins/{user_id}", status_code=status.HTTP_200_OK)
async def remove_project_admin(
    project_id: UUID,
    user_id: UUID,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_org_admin),
    db: AsyncSession = Depends(get_session),
):
    project_belongs = await verify_project_belongs_to_org(
        db, project_id, principal.organization_id
    )
    if not project_belongs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or does not belong to your organization"
        )
    
    user_in_org = await verify_user_in_org(
        db, user_id, principal.organization_id
    )
    if not user_in_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or does not belong to your organization"
        )
    
    user_role_id = await get_user_project_admin_role(db, user_id, project_id)
    if not user_role_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have PROJECT_ADMIN role on this project"
        )
    
    deleted = await delete_user_role(db, user_role_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove project admin role"
        )
    
    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role_id,
        action="REVOKE_PROJECT_ADMIN",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "target_user_id": str(user_id),
            "project_id": str(project_id),
            "role": "PROJECT_ADMIN",
            "revoked_by_org_admin": True
        }
    )
    
    await db.commit()
    
    return {
        "message": "Project admin role removed successfully",
        "user_id": str(user_id),
        "project_id": str(project_id)
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_user(
    user_id: UUID,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_org_admin),
    db: AsyncSession = Depends(get_session),
):
    if user_id == principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user account"
        )
    
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.organization_id != principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to your organization"
        )
    
    await write_audit_event(
        db,
        entity_type="user",
        entity_id=user_id,
        action="DELETE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "deleted_user_email": user.email,
            "deleted_by_org_admin": True
        }
    )
    
    await delete_all_user_roles_for_user(db, user_id)
    await update_user(db, user, UserUpdate(is_active=False, organization_id=None))
    await db.commit()
    return None
