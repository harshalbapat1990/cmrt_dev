from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import Principal, get_current_principal
from core.session import get_session


GLOBAL = "GLOBAL"
ORGANISATION = "ORGANISATION"
PROJECT = "PROJECT"
STAGE = "STAGE"

VALID_SCOPE_TYPES = {GLOBAL, ORGANISATION, PROJECT, STAGE}

SUPER_ADMIN  = "SUPER_ADMIN"
ORG_ADMIN    = "ORG_ADMIN"
PROJECT_ADMIN  = "PROJECT_ADMIN"
PROJECT_EDITOR = "PROJECT_EDITOR"
PROJECT_VIEWER = "PROJECT_VIEWER"
GENERAL_USER   = "GENERAL_USER"   # NOTE: Auto-assigned on registration; no project access until explicitly granted a project role

_GRANT_CEILING: dict[str, set[str]] = {
    SUPER_ADMIN:    {SUPER_ADMIN, ORG_ADMIN},
    ORG_ADMIN:      {PROJECT_ADMIN},
    PROJECT_ADMIN:  {PROJECT_EDITOR, PROJECT_VIEWER},
}


async def get_effective_role_names(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
) -> set[str]:
    from models.user_roles import UserRole
    from models.roles import Role
    from sqlalchemy import or_, literal

    scope_conditions = [
        UserRole.scope_type == GLOBAL,
    ]

    if project_id:
        from models.project import Project
        from models.project_stage_instances import ProjectStageInstance

        org_subq = (
            select(Project.proponent_org_id)
            .where(Project.id == project_id)
            .scalar_subquery()
        )
        stage_subq = (
            select(ProjectStageInstance.id)
            .where(ProjectStageInstance.project_id == project_id)
            .scalar_subquery()
        )

        scope_conditions += [
            (UserRole.scope_type == PROJECT) & (UserRole.scope_id == project_id),
            (UserRole.scope_type == ORGANISATION) & (UserRole.scope_id == org_subq),
            (UserRole.scope_type == STAGE) & (UserRole.scope_id.in_(stage_subq)),
        ]

    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            or_(*scope_conditions),
        )
        .distinct()
    )
    return set(result.scalars().all())


async def get_stage_role_names(
    db: AsyncSession,
    user_id: uuid.UUID,
    stage_instance_id: uuid.UUID,
) -> set[str]:
    """Return active roles explicitly assigned to a user for one stage."""

    from models.user_roles import UserRole
    from models.roles import Role

    result = await db.execute(
        select(Role.name)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == STAGE,
            UserRole.scope_id == stage_instance_id,
        )
        .distinct()
    )

    return set(result.scalars().all())


async def get_stage_access_level(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    stage_instance_id: uuid.UUID,
):
    """
    Resolve the user's effective access to one project stage.

    Access precedence:

        ORG_ADMIN for the project's organisation
            -> ADMIN

        PROJECT_ADMIN on the project
            -> ADMIN

        STAGE PROJECT_EDITOR
            -> EDIT

        STAGE PROJECT_VIEWER
            -> VIEW

        no applicable role
            -> NONE

    SUPER_ADMIN intentionally does NOT grant project/stage access.

    A stage must:
        1. exist,
        2. belong to the supplied project,
        3. currently be enabled.

    Historical retained stage instances therefore cannot provide access
    while their stage is disabled.
    """

    from core.authorization_policy import (
        AccessLevel,
        PROJECT_ADMIN_ROLES,
        stage_access_for_role,
    )
    from models.project_stage_instances import ProjectStageInstance
    from models.project_stage_config import ProjectStageConfig

    # ------------------------------------------------------------------
    # 1. Resolve the stage and verify that it belongs to this project.
    # ------------------------------------------------------------------

    stage_result = await db.execute(
        select(
            ProjectStageInstance.project_id,
            ProjectStageInstance.stage,
        ).where(
            ProjectStageInstance.id == stage_instance_id,
        )
    )

    stage_row = stage_result.one_or_none()

    if stage_row is None:
        return AccessLevel.NONE

    stage_project_id, stage = stage_row

    if stage_project_id != project_id:
        return AccessLevel.NONE

    # ------------------------------------------------------------------
    # 2. Verify that the stage is currently enabled.
    #
    # BUSINESS_CASE / DESIGN / CONSTRUCTION:
    #     enabled state comes from ProjectStageConfig.
    #
    # RECURRING:
    #     ProjectStageConfig does not contain RECURRING.
    #     Its existence is controlled by project.project_class.
    #
    # The stage instance is deliberately retained when disabled so that
    # historical data and its UUID remain stable. It must nevertheless
    # provide NO authorization while disabled.
    # ------------------------------------------------------------------

    if stage.value in {
        "BUSINESS_CASE",
        "DESIGN",
        "CONSTRUCTION",
    }:
        config_result = await db.execute(
            select(ProjectStageConfig.enabled).where(
                ProjectStageConfig.project_id == project_id,
                ProjectStageConfig.stage == stage.value,
            )
        )

        enabled = config_result.scalar_one_or_none()

        if enabled is not True:
            return AccessLevel.NONE

    elif stage.value == "RECURRING":
        from models.project import Project

        project_result = await db.execute(
            select(Project.project_class).where(
                Project.id == project_id,
            )
        )

        project_class = project_result.scalar_one_or_none()

        if project_class is None:
            return AccessLevel.NONE

        project_class_value = getattr(
            project_class,
            "value",
            project_class,
        )

        if project_class_value != "RECURRING":
            return AccessLevel.NONE

    else:
        # Unknown/future stage types must fail closed until their
        # enablement semantics are explicitly implemented.
        return AccessLevel.NONE

    # ------------------------------------------------------------------
    # 3. Resolve broader project-level administrative roles.
    # ------------------------------------------------------------------

    effective_project_roles = await get_effective_role_names(
        db,
        user_id,
        project_id=project_id,
    )

    if effective_project_roles.intersection(PROJECT_ADMIN_ROLES):
        return AccessLevel.ADMIN

    # ------------------------------------------------------------------
    # 4. Resolve explicit stage assignments.
    # ------------------------------------------------------------------

    stage_roles = await get_stage_role_names(
        db,
        user_id,
        stage_instance_id,
    )

    effective_access = AccessLevel.NONE

    for role_name in stage_roles:
        role_access = stage_access_for_role(role_name)

        if role_access > effective_access:
            effective_access = role_access

    return effective_access


async def require_stage_access(
    db: AsyncSession,
    principal: Principal,
    project_id: uuid.UUID,
    stage_instance_id: uuid.UUID,
    minimum_access,
) -> None:
    """
    Require a minimum access level to one specific project stage.

    This is the backend security boundary for stage-scoped operations.

    Access levels:
        NONE  -> no access
        VIEW  -> read only
        EDIT  -> read/create/update/delete
        ADMIN -> full stage administration

    PROJECT_ADMIN and ORG_ADMIN resolve to ADMIN through
    get_stage_access_level().

    SUPER_ADMIN does not automatically receive project/stage access.
    """

    from core.authorization_policy import AccessLevel

    access = await get_stage_access_level(
        db=db,
        user_id=principal.user_id,
        project_id=project_id,
        stage_instance_id=stage_instance_id,
    )

    if access < minimum_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Insufficient access to stage "
                f"{stage_instance_id}. "
                f"Required: {minimum_access.name}, "
                f"actual: {access.name}"
            ),
        )


async def get_project_access_level(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
):
    """
    Resolve effective access to the project as a whole.

    Project-level access is intentionally different from access to one
    particular stage:

        ORG_ADMIN for the project's organisation -> ADMIN
        PROJECT_ADMIN on the project             -> ADMIN
        any active stage EDIT assignment          -> EDIT
        any active stage VIEW assignment          -> VIEW
        no applicable access                      -> NONE

    SUPER_ADMIN does not automatically receive project access.

    PROJECT_ADMIN / ORG_ADMIN remain able to administer a project even when
    every individual stage is disabled, because project administration is
    required to change stage configuration.
    """

    from core.authorization_policy import AccessLevel, PROJECT_ADMIN_ROLES
    from models.project_stage_instances import ProjectStageInstance

    effective_project_roles = await get_effective_role_names(
        db,
        user_id,
        project_id=project_id,
    )

    if effective_project_roles.intersection(PROJECT_ADMIN_ROLES):
        return AccessLevel.ADMIN

    result = await db.execute(
        select(ProjectStageInstance.id).where(
            ProjectStageInstance.project_id == project_id,
        )
    )

    stage_ids = result.scalars().all()

    effective_access = AccessLevel.NONE

    for stage_instance_id in stage_ids:
        stage_access = await get_stage_access_level(
            db=db,
            user_id=user_id,
            project_id=project_id,
            stage_instance_id=stage_instance_id,
        )

        if stage_access > effective_access:
            effective_access = stage_access

        if effective_access == AccessLevel.EDIT:
            break

    return effective_access


async def require_project_access(
    db: AsyncSession,
    principal: Principal,
    project_id: uuid.UUID,
    minimum_access,
) -> None:
    """
    Require a minimum effective access level to the project.
    """

    from core.authorization_policy import AccessLevel

    access = await get_project_access_level(
        db=db,
        user_id=principal.user_id,
        project_id=project_id,
    )

    if access < minimum_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Insufficient access to project {project_id}. "
                f"Required: {minimum_access.name}, actual: {access.name}"
            ),
        )

   
async def get_org_scoped_role_names(
    db: AsyncSession,
    user_id: uuid.UUID,
    organisation_id: uuid.UUID,
) -> set[str]:
    from models.user_roles import UserRole
    from models.roles import Role
    from sqlalchemy import or_

    query = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            or_(
                UserRole.scope_type == GLOBAL,
                (UserRole.scope_type == ORGANISATION) & (UserRole.scope_id == organisation_id),
            ),
        )
    )
    result = await db.execute(query)
    return set(result.scalars().all())


async def get_all_role_names_for_ui(
    db: AsyncSession,
    user_id: uuid.UUID,
    organisation_id: Optional[uuid.UUID] = None,
) -> set[str]:
    from models.user_roles import UserRole
    from models.roles import Role
    from sqlalchemy import or_

    scope_conditions = [
        UserRole.scope_type == GLOBAL,
        UserRole.scope_type == PROJECT,
    ]
    if organisation_id:
        scope_conditions.append(
            (UserRole.scope_type == ORGANISATION) & (UserRole.scope_id == organisation_id)
        )

    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            or_(*scope_conditions),
        )
        .distinct()
    )
    return set(result.scalars().all())


async def get_any_project_role_names(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> set[str]:
    """
    Return project-access roles held by a user at either PROJECT or STAGE
    scope.

    This is intentionally an aggregate helper. It does not determine
    access to a specific stage.
    """

    from models.user_roles import UserRole
    from models.roles import Role
    from models.project_stage_instances import (
        ProjectStageInstance,
    )

    project_roles_result = await db.execute(
        select(Role.name)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == PROJECT,
            Role.name == PROJECT_ADMIN,
        )
        .distinct()
    )

    roles = set(
        project_roles_result.scalars().all()
    )

    stage_roles_result = await db.execute(
        select(Role.name)
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .join(
            ProjectStageInstance,
            ProjectStageInstance.id
            == UserRole.scope_id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == STAGE,
            Role.name.in_(
                [
                    PROJECT_EDITOR,
                    PROJECT_VIEWER,
                ]
            ),
        )
        .distinct()
    )

    roles.update(
        stage_roles_result.scalars().all()
    )

    return roles


async def get_project_ids_where_admin(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[uuid.UUID]:
    from models.user_roles import UserRole
    from models.roles import Role

    result = await db.execute(
        select(UserRole.scope_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active == True,
            UserRole.scope_type == PROJECT,
            Role.name == PROJECT_ADMIN,
        )
    )
    return [i for i in result.scalars().all() if i is not None]


async def validate_scope(
    db: AsyncSession,
    scope_type: str,
    scope_id: Optional[uuid.UUID],
    *,
    caller: Optional[Principal] = None,
) -> None:
    if scope_type not in VALID_SCOPE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scope_type must be one of {sorted(VALID_SCOPE_TYPES)}",
        )
    if scope_type == GLOBAL and scope_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scope_id must be null when scope_type=GLOBAL",
        )
    if scope_type != GLOBAL and scope_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scope_id is required when scope_type={scope_type}",
        )

    if scope_type == ORGANISATION:
        from models.organizations import Organization
        res = await db.execute(select(Organization).where(Organization.id == scope_id))
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    elif scope_type == PROJECT:
        from models.project import Project
        res = await db.execute(select(Project).where(Project.id == scope_id))
        proj = res.scalars().first()
        if not proj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    elif scope_type == STAGE:
        from models.project_stage_instances import ProjectStageInstance
        res = await db.execute(
            select(ProjectStageInstance).where(ProjectStageInstance.id == scope_id)
        )
        if not res.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found")


async def assert_can_grant_role(
    db: AsyncSession,
    caller: Principal,
    target_role_name: str,
    scope_type: str,
    scope_id: Optional[uuid.UUID],
) -> None:
    if scope_type == PROJECT:
        caller_roles = await get_effective_role_names(db, caller.user_id, project_id=scope_id)
    elif scope_type == ORGANISATION:
        caller_roles = await get_org_scoped_role_names(db, caller.user_id, scope_id)
    else:
        caller_roles = await get_effective_role_names(db, caller.user_id)

    allowed_to_grant: set[str] = set()
    for role in caller_roles:
        allowed_to_grant |= _GRANT_CEILING.get(role, set())

    if target_role_name not in allowed_to_grant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to grant the '{target_role_name}' role at this scope",
        )


def require_role(*role_names: str, project_id_param: Optional[str] = None):

    async def _dep(
        request: Request,
        principal: Principal = Depends(get_current_principal),
        db: AsyncSession = Depends(get_session),
    ):
        project_id: Optional[uuid.UUID] = None
        if project_id_param:
            raw = request.path_params.get(project_id_param) or request.query_params.get(project_id_param)
            if raw:
                try:
                    project_id = uuid.UUID(str(raw))
                except ValueError:
                    pass

        effective_roles = set(await get_effective_role_names(db, principal.user_id, project_id=project_id))
        if not effective_roles.intersection(role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {list(role_names)}",
            )

    return _dep


async def require_org_admin(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
) -> None:
    if not principal.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )
    
    org_roles = await get_org_scoped_role_names(db, principal.user_id, principal.organization_id)
    
    if ORG_ADMIN not in org_roles and SUPER_ADMIN not in org_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ORG_ADMIN role required"
        )


