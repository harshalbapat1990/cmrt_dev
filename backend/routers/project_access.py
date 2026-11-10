from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# from core.rbac import (
#     ORG_ADMIN,
#     get_org_scoped_role_names,
# )

from core.rbac import (
    ORG_ADMIN,
    SUPER_ADMIN,
    get_effective_role_names,
    get_org_scoped_role_names,
)
from core.authorization_policy import (
    can_manage_project_user_access
)
from core.security import (
    Principal,
    get_current_principal,
)
from core.session import get_session

from crud.audit_logs import write_audit_event
from crud.project_access import (
    get_project_access,
    update_user_stage_access,
)

from schemas.project_access import (
    ProjectAccessOut,
    ProjectUserSearchResult,
    UpdateUserStageAccessIn,
)
from models.users import User
from models.roles import Role
from models.user_roles import UserRole


router = APIRouter(
    prefix="/api/projects",
    tags=["project-access"],
)


async def _require_project_user_manager(
    db: AsyncSession,
    principal: Principal,
    project_id: UUID,
) -> None:
    role_names = await get_effective_role_names(
        db,
        principal.user_id,
        project_id=project_id,
    )

    if not can_manage_project_user_access(role_names):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project user management permission required",
        )
    

@router.get(
    "/{project_id}/user-search",
    response_model=list[ProjectUserSearchResult],
)
async def search_project_access_users(
    project_id: UUID,
    q: str = Query(..., min_length=2, max_length=254),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    await _require_project_user_manager(db, principal, project_id)
    needle = q.strip()
    if len(needle) < 2:
        return []
    rows = await db.execute(
        select(User.id, User.email, User.first_name, User.last_name)
        .where(User.is_active.is_(True),
               or_(User.email.ilike(f"%{needle}%"),
                   User.first_name.ilike(f"%{needle}%"),
                   User.last_name.ilike(f"%{needle}%")))
        .order_by(User.email)
        .limit(20)
    )
    return [
        ProjectUserSearchResult(
            user_id=row.id,
            email=row.email,
            display_name=" ".join(part for part in (row.first_name, row.last_name) if part).strip() or row.email,
        )
        for row in rows.all()
    ]


@router.get(
    "/setup-user-search",
    response_model=list[ProjectUserSearchResult],
)
async def search_project_setup_users(
    organisation_id: UUID,
    q: str = Query(..., min_length=2, max_length=254),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    """Search active registered users while an authorized admin creates a project."""
    org_roles = await get_org_scoped_role_names(
        db, principal.user_id, organisation_id
    )
    if not org_roles.intersection({ORG_ADMIN, SUPER_ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation administrator permission required to add project users",
        )

    needle = q.strip()
    if len(needle) < 2:
        return []
    rows = await db.execute(
        select(User.id, User.email, User.first_name, User.last_name)
        .where(
            User.is_active.is_(True),
            or_(
                User.email.ilike(f"%{needle}%"),
                User.first_name.ilike(f"%{needle}%"),
                User.last_name.ilike(f"%{needle}%"),
            ),
        )
        .order_by(User.email)
        .limit(20)
    )
    return [
        ProjectUserSearchResult(
            user_id=row.id,
            email=row.email,
            display_name=" ".join(
                part for part in (row.first_name, row.last_name) if part
            ).strip() or row.email,
        )
        for row in rows.all()
    ]


@router.get(
    "/{project_id}/access",
    response_model=ProjectAccessOut,
)
async def get_project_access_endpoint(
    project_id: UUID,
    principal: Principal = Depends(
        get_current_principal
    ),
    db: AsyncSession = Depends(
        get_session
    ),
):
    await _require_project_user_manager(
        db,
        principal,
        project_id,
    )

    return await get_project_access(
        db,
        project_id,
    )


@router.put(
    "/{project_id}/users/{user_id}/stage-access",
    response_model=ProjectAccessOut,
)
async def update_project_user_stage_access_endpoint(
    project_id: UUID,
    user_id: UUID,
    payload: UpdateUserStageAccessIn,
    principal: Principal = Depends(
        get_current_principal
    ),
    db: AsyncSession = Depends(
        get_session
    ),
):
    await _require_project_user_manager(
        db,
        principal,
        project_id,
    )

    target_result = await db.execute(
        select(User.id).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )
    if target_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    project_admin_result = await db.execute(
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id,
               UserRole.scope_type == "PROJECT",
               UserRole.scope_id == project_id,
               UserRole.is_active.is_(True),
               Role.name == "PROJECT_ADMIN")
        .limit(1)
    )
    if project_admin_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail="Project Admin roles are managed separately by an Organisation Admin.")

    before = await get_project_access(db, project_id)
    previous = next((member for member in before.members if member.user_id == user_id), None)
    result = await update_user_stage_access(
        db,
        project_id,
        user_id,
        payload,
    )

    await write_audit_event(
        db,
        entity_type="project_stage_access",
        entity_id=project_id,
        action="REPLACE_STAGE_ACCESS",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "target_user_id": str(user_id),
            "project_id": str(project_id),
            "before": [
                {"stage_instance_id": str(item.stage_instance_id), "access": item.access}
                for item in (previous.assignments if previous else [])
            ],
            "assignments": [
                {
                    "stage_instance_id": str(
                        assignment.stage_instance_id
                    ),
                    "access": assignment.access.value,
                }
                for assignment in payload.assignments
            ],
        },
    )

    await db.commit()

    return result
