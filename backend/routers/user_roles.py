from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select

from core.rbac import assert_can_grant_role, validate_scope, SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, get_effective_role_names, get_org_scoped_role_names, get_project_ids_where_admin, require_role
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.roles import get_role, get_role_by_name
from schemas.user_roles import UserRoleOut, UserRoleCreate, UserRoleUpdate, UserRoleEnrichedOut, TransferOrgAdminRequest, AssignOrgAdminRequest
from crud.user_roles import (
    create_user_role,
    list_user_roles,
    list_user_roles_enriched,
    get_user_role,
    update_user_role,
    delete_user_role
)
from models.user_roles import UserRole

router = APIRouter(prefix="/api/user-roles", tags=["user-roles"])


class SuperAdminAssignRequest(BaseModel):
    user_id: UUID


@router.get("/super-admins")
async def list_super_admin_assignments(
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    return await list_user_roles_enriched(
        db, role_name=SUPER_ADMIN, scope_type="GLOBAL", limit=1000
    )


@router.get("/super-admins/assignable-users")
async def search_super_admin_targets(
    search: str = Query("", max_length=120),
    limit: int = Query(100, ge=1, le=250),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    from models.users import User

    role = await get_role_by_name(db, SUPER_ADMIN)
    if role is None:
        return []
    active_assignment = select(UserRole.id).where(
        UserRole.user_id == User.id,
        UserRole.role_id == role.id,
        UserRole.scope_type == "GLOBAL",
        UserRole.scope_id.is_(None),
        UserRole.is_active == True,
    ).exists()
    query = select(
        User.id.label("user_id"),
        User.email,
        func.nullif(func.trim(func.coalesce(User.first_name, "") + " " + func.coalesce(User.last_name, "")), "").label("display_name"),
    ).where(User.is_active == True, ~active_assignment)
    normalized = search.strip()
    if normalized:
        pattern = f"%{normalized}%"
        query = query.where(or_(User.email.ilike(pattern), User.first_name.ilike(pattern), User.last_name.ilike(pattern)))
    result = await db.execute(query.order_by(User.email).limit(limit))
    return [
        {"user_id": str(row.user_id), "email": row.email, "display_name": row.display_name}
        for row in result.all()
    ]


@router.post("/super-admins", status_code=status.HTTP_201_CREATED)
async def assign_super_admin(
    payload: SuperAdminAssignRequest,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    from models.users import User

    target = await db.get(User, payload.user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found")
    role = await get_role_by_name(db, SUPER_ADMIN)
    if role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPER_ADMIN role is not configured")
    existing_result = await db.execute(select(UserRole).where(
        UserRole.user_id == target.id,
        UserRole.role_id == role.id,
        UserRole.scope_type == "GLOBAL",
        UserRole.scope_id.is_(None),
    ).limit(1))
    assignment = existing_result.scalars().first()
    if assignment and assignment.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has Super Admin access")
    if assignment:
        assignment.is_active = True
        await db.flush()
        action = "REACTIVATE_SUPER_ADMIN"
    else:
        assignment = await create_user_role(db, target.id, role.id, "GLOBAL", None, True)
        action = "GRANT_SUPER_ADMIN"
    await write_audit_event(
        db, entity_type="user_role", entity_id=assignment.id, action=action,
        performed_by=principal.user_id, performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(target.id), "role": SUPER_ADMIN, "scope_type": "GLOBAL"},
    )
    await db.commit()
    return {"user_role_id": str(assignment.id), "user_id": str(target.id), "email": target.email, "role": SUPER_ADMIN, "is_active": True}


@router.post("", response_model=UserRoleOut, status_code=status.HTTP_201_CREATED)
async def create_new_user_role(
    payload: UserRoleCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    await validate_scope(db, payload.scope_type, payload.scope_id, caller=principal)

    role = await get_role(db, payload.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    await assert_can_grant_role(db, principal, role.name, payload.scope_type, payload.scope_id)

    user_role = await create_user_role(
        db,
        payload.user_id,
        payload.role_id,
        payload.scope_type,
        payload.scope_id,
        payload.is_active,
    )
    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role.id,
        action="GRANT",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "target_user_id": str(payload.user_id),
            "role": role.name,
            "scope_type": payload.scope_type,
            "scope_id": str(payload.scope_id) if payload.scope_id else None,
        },
    )
    await db.commit()
    return user_role


@router.get("", response_model=List[UserRoleOut])
async def get_user_roles(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    role_id: Optional[UUID] = Query(None, description="Filter by role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    scope_type: Optional[str] = Query(None, description="Filter by scope type (GLOBAL|ORGANISATION|PROJECT|STAGE)"),
    scope_id: Optional[UUID] = Query(None, description="Filter by scope ID — use with scope_type=PROJECT to list all members of a project"),
    _: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    user_roles = await list_user_roles(
        db, skip, limit, user_id, role_id, is_active,
        scope_type=scope_type, scope_id=scope_id,
    )
    return user_roles


@router.get("/enriched", response_model=List[UserRoleEnrichedOut])
async def get_user_roles_enriched(
    role_name: Optional[str] = Query(None, description="Filter by role name, e.g. ORG_ADMIN, PROJECT_ADMIN"),
    scope_type: Optional[str] = Query(None, description="Filter by scope type: GLOBAL|ORGANISATION|PROJECT"),
    limit: int = Query(200, ge=1, le=1000),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    
    if principal.organization_id is not None:
        effective_roles = await get_org_scoped_role_names(db, principal.user_id, principal.organization_id)
    else:
        effective_roles = await get_effective_role_names(db, principal.user_id)

    scope_ids: Optional[List[UUID]] = None

    if SUPER_ADMIN not in effective_roles:
        if ORG_ADMIN in effective_roles:
            if scope_type and scope_type.upper() == "ORGANISATION":
                if principal.organization_id:
                    scope_ids = [principal.organization_id]
                else:
                    return []
            else:
                from sqlalchemy.future import select as sa_select
                from models.project import Project
                from models.project_organizations import ProjectOrganization

                proponent_q = await db.execute(
                    sa_select(Project.id).where(
                        Project.proponent_org_id == principal.organization_id
                    )
                )
                secondary_q = await db.execute(
                    sa_select(ProjectOrganization.project_id).where(
                        ProjectOrganization.organization_id == principal.organization_id
                    )
                )
                scope_ids = list({
                    pid
                    for pid in [*proponent_q.scalars().all(), *secondary_q.scalars().all()]
                    if pid is not None
                })
                if not scope_ids:
                    return []
        elif PROJECT_ADMIN in effective_roles:
            scope_ids = await get_project_ids_where_admin(db, principal.user_id)
            if not scope_ids:
                return []
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return await list_user_roles_enriched(
        db,
        role_name=role_name,
        scope_type=scope_type,
        scope_ids=scope_ids,
        limit=limit,
    )


@router.get("/{user_role_id}", response_model=UserRoleOut)
async def get_user_role_by_id(
    user_role_id: UUID,
    _: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    user_role = await get_user_role(db, user_role_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User-Role mapping not found"
        )
    return user_role


@router.post("/assign-org-admin", status_code=status.HTTP_201_CREATED)
async def assign_org_admin(
    payload: AssignOrgAdminRequest,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    from models.users import User
    from sqlalchemy import select, and_
    from models.user_roles import UserRole as UserRoleModel

    target_user = await db.get(User, payload.user_id)
    if target_user is None or target_user.organization_id != payload.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in that organisation")

    org_admin_role = await get_role_by_name(db, ORG_ADMIN)
    if not org_admin_role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ORG_ADMIN role not found in system")

    existing_active = await db.execute(
        select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == payload.user_id,
                UserRoleModel.role_id == org_admin_role.id,
                UserRoleModel.scope_type == "ORGANISATION",
                UserRoleModel.scope_id == payload.org_id,
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
                UserRoleModel.scope_id == payload.org_id,
                UserRoleModel.is_active == False,
            )
        )
    )
    inactive_ur = existing_inactive.scalars().first()
    if inactive_ur:
        new_ur = await update_user_role(db, inactive_ur.id, is_active=True)
    else:
        new_ur = await create_user_role(
            db,
            user_id=payload.user_id,
            role_id=org_admin_role.id,
            scope_type="ORGANISATION",
            scope_id=payload.org_id,
            is_active=True,
        )
    await write_audit_event(
        db, entity_type="user_role", entity_id=new_ur.id,
        action="GRANT_ORG_ADMIN", performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(payload.user_id), "org_id": str(payload.org_id), "granted_by_super_admin": True},
    )
    await db.commit()
    return {"message": "ORG_ADMIN role assigned successfully", "user_role_id": str(new_ur.id)}


@router.post("/transfer-org-admin", status_code=status.HTTP_200_OK)
async def transfer_org_admin(
    payload: TransferOrgAdminRequest,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    from models.users import User
    from sqlalchemy import select, and_
    from models.user_roles import UserRole as UserRoleModel

    active_ur_res = await db.execute(
        select(UserRoleModel).where(
            and_(UserRoleModel.id == payload.from_user_role_id, UserRoleModel.is_active == True)
        )
    )
    from_ur = active_ur_res.scalars().first()
    if not from_ur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source user role not found or already inactive")

    from_role = await get_role(db, from_ur.role_id)
    if from_role is None or from_role.name != ORG_ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source role must be an active ORG_ADMIN role")

    if from_ur.scope_type != "ORGANISATION" or from_ur.scope_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source role must be organisation-scoped")

    org_id = from_ur.scope_id

    to_user = await db.get(User, payload.to_user_id)
    if to_user is None or to_user.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found in that organisation")

    existing_active = await db.execute(
        select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == payload.to_user_id,
                UserRoleModel.role_id == from_ur.role_id,
                UserRoleModel.scope_type == "ORGANISATION",
                UserRoleModel.scope_id == org_id,
                UserRoleModel.is_active == True,
            )
        )
    )
    if existing_active.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target user is already an ORG_ADMIN for this organisation")

    await update_user_role(db, payload.from_user_role_id, is_active=False)

    existing_inactive = await db.execute(
        select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == payload.to_user_id,
                UserRoleModel.role_id == from_ur.role_id,
                UserRoleModel.scope_type == "ORGANISATION",
                UserRoleModel.scope_id == org_id,
                UserRoleModel.is_active == False,
            )
        )
    )
    inactive_ur = existing_inactive.scalars().first()
    if inactive_ur:
        new_ur = await update_user_role(db, inactive_ur.id, is_active=True)
    else:
        new_ur = await create_user_role(
            db,
            user_id=payload.to_user_id,
            role_id=from_ur.role_id,
            scope_type="ORGANISATION",
            scope_id=org_id,
            is_active=True,
    )

    await write_audit_event(
        db, entity_type="user_role", entity_id=from_ur.id,
        action="REVOKE_ORG_ADMIN", performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(from_ur.user_id), "org_id": str(org_id), "transferred_to": str(payload.to_user_id)},
    )
    await write_audit_event(
        db, entity_type="user_role", entity_id=new_ur.id,
        action="GRANT_ORG_ADMIN", performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(payload.to_user_id), "org_id": str(org_id), "transferred_from": str(from_ur.user_id)},
    )
    await db.commit()
    return {"message": "ORG_ADMIN role transferred successfully", "new_user_role_id": str(new_ur.id)}


@router.patch("/{user_role_id}", response_model=UserRoleOut)
async def update_user_role_by_id(
    user_role_id: UUID,
    payload: UserRoleUpdate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    if payload.is_active is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="is_active must be provided")
    user_role = await get_user_role(db, user_role_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User-Role mapping not found"
        )

    target_role = await get_role(db, user_role.role_id)
    if target_role is not None and target_role.name == ORG_ADMIN and payload.is_active is False:
        caller_roles = await get_effective_role_names(db, principal.user_id)
        if SUPER_ADMIN not in caller_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPER_ADMIN can revoke an ORG_ADMIN role")

    super_admin_change = target_role is not None and target_role.name == SUPER_ADMIN
    if super_admin_change:
        caller_roles = await get_effective_role_names(db, principal.user_id)
        if SUPER_ADMIN not in caller_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPER_ADMIN can change a SUPER_ADMIN role")
        if user_role.scope_type != "GLOBAL" or user_role.scope_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="SUPER_ADMIN assignments must use GLOBAL scope")
        if payload.is_active is False and user_role.is_active:
            active_count = await db.execute(select(func.count(UserRole.id)).where(
                UserRole.role_id == user_role.role_id,
                UserRole.scope_type == "GLOBAL",
                UserRole.scope_id.is_(None),
                UserRole.is_active == True,
            ))
            if int(active_count.scalar_one() or 0) <= 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The final active Super Admin cannot be removed")

    user_role = await update_user_role(db, user_role_id, is_active=payload.is_active)
    action = (
        "REVOKE_SUPER_ADMIN" if super_admin_change and payload.is_active is False
        else "REACTIVATE_SUPER_ADMIN" if super_admin_change and payload.is_active is True
        else "REVOKE" if payload.is_active is False
        else "REACTIVATE"
    )
    metadata = {"target_user_id": str(user_role.user_id)}
    if target_role is not None:
        metadata["role"] = target_role.name
    await write_audit_event(
        db,
        entity_type="user_role",
        entity_id=user_role_id,
        action=action,
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata=metadata,
    )
    await db.commit()
    return user_role


@router.delete("/{user_role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_role(
    user_role_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    user_role = await get_user_role(db, user_role_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User-Role mapping not found"
        )
    target_role = await get_role(db, user_role.role_id)
    caller_roles = await get_effective_role_names(db, principal.user_id)
    if SUPER_ADMIN not in caller_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPER_ADMIN can delete user-role assignments")
    if target_role is not None and target_role.name == SUPER_ADMIN:
        if user_role.scope_type != "GLOBAL" or user_role.scope_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="SUPER_ADMIN assignments must use GLOBAL scope")
        if user_role.is_active:
            active_count = await db.execute(select(func.count(UserRole.id)).where(
                UserRole.role_id == user_role.role_id,
                UserRole.scope_type == "GLOBAL",
                UserRole.scope_id.is_(None),
                UserRole.is_active == True,
            ))
            if int(active_count.scalar_one() or 0) <= 1:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The final active Super Admin cannot be removed")
        # Preserve assignment history and enforce the same last-admin rule as PATCH.
        user_role.is_active = False
        await db.flush()
        action = "REVOKE_SUPER_ADMIN"
        metadata = {"target_user_id": str(user_role.user_id), "role": SUPER_ADMIN, "scope_type": "GLOBAL"}
        await write_audit_event(
            db, entity_type="user_role", entity_id=user_role.id, action=action,
            performed_by=principal.user_id, performed_by_org=principal.organization_id,
            metadata=metadata,
        )
        await db.commit()
        return None

    ok = await delete_user_role(db, user_role_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User-Role mapping not found")
    await write_audit_event(
        db, entity_type="user_role", entity_id=user_role_id, action="DELETE",
        performed_by=principal.user_id, performed_by_org=principal.organization_id,
        metadata={"target_user_id": str(user_role.user_id), "role": target_role.name if target_role else None},
    )
    await db.commit()
    return None
