from __future__ import annotations

from typing import Dict, List, Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.roles import Role
from models.user_roles import UserRole
from models.users import User
from schemas.project_access import (
    ProjectAccessMemberOut,
    ProjectAccessOut,
    ProjectStageAccessOut,
    UpdateUserStageAccessIn,
)

from models.project_stage_config import ProjectStageConfig 
from models.project_stage_instances import (
    ProjectStageInstance,
    ProjectStage,
)

from models.project_stage_config import ProjectStageConfig

_STAGE_ROLE_NAMES = (
    "PROJECT_VIEWER",
    "PROJECT_EDITOR",
)


_STAGE_LABELS = {
    "BUSINESS_CASE": "Business case",
    "DESIGN": "Design",
    "CONSTRUCTION": "Construction",
    "RECURRING": "Recurring",
}


def _stage_label(stage: str) -> str:
    """
    Convert the database enum value into the UI display label.

    Unknown future stages are still handled gracefully.
    """
    return _STAGE_LABELS.get(
        stage,
        stage.replace("_", " ").title(),
    )


async def _get_project_or_404(
    db: AsyncSession,
    project_id: UUID,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )

    project = result.scalars().first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


async def _get_project_stages(
    db: AsyncSession,
    project_id: UUID,
) -> List[ProjectStageInstance]:
    result = await db.execute(
        select(ProjectStageInstance)
        .where(
            ProjectStageInstance.project_id == project_id
        )
        .order_by(
            ProjectStageInstance.sequence,
            ProjectStageInstance.stage,
        )
    )

    return list(result.scalars().all())


async def get_project_access(
    db: AsyncSession,
    project_id: UUID,
) -> ProjectAccessOut:
    """
    Return the complete stage-access picture for a project.

    The response contains:

        project
        stages
        members
        each member's stage assignments

    Ordinary project membership comes from active STAGE-scoped
    PROJECT_VIEWER / PROJECT_EDITOR roles.

    PROJECT_ADMIN remains project-scoped and therefore receives ADMIN
    access to every stage.
    """

    project = await _get_project_or_404(
        db,
        project_id,
    )

    stages = await _get_project_stages(
        db,
        project_id,
    )

    stage_ids = [
        stage.id
        for stage in stages
    ]

    members_by_user: Dict[UUID, dict] = {}

    # ------------------------------------------------------------------
    # Ordinary project members
    # ------------------------------------------------------------------
    #
    # Only STAGE-scoped viewer/editor roles are considered.
    #
    # This is intentional. Existing PROJECT_EDITOR / PROJECT_VIEWER
    # assignments will be migrated in Phase 3.
    # ------------------------------------------------------------------

    if stage_ids:
        result = await db.execute(
            select(
                UserRole.id,
                UserRole.user_id,
                UserRole.scope_id,
                Role.name,
                User.email,
                User.first_name,
                User.last_name,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .join(
                User,
                User.id == UserRole.user_id,
            )
            .where(
                UserRole.scope_type == "STAGE",
                UserRole.scope_id.in_(stage_ids),
                UserRole.is_active == True,
                Role.name.in_(_STAGE_ROLE_NAMES),
                User.is_active == True,
            )
        )

        rows = result.all()

        stage_by_id = {
            stage.id: stage
            for stage in stages
        }

        for row in rows:
            stage = stage_by_id[row.scope_id]

            display_name = " ".join(
                part
                for part in (
                    row.first_name,
                    row.last_name,
                )
                if part
            ).strip()

            member = members_by_user.setdefault(
                row.user_id,
                {
                    "user_id": row.user_id,
                    "display_name": display_name or row.email,
                    "email": row.email,
                    "assignments": {},
                },
            )

            access = (
                "EDIT"
                if row.name == "PROJECT_EDITOR"
                else "VIEW"
            )

            stage_value = (
                stage.stage.value
                if hasattr(stage.stage, "value")
                else str(stage.stage)
            )

            member["assignments"][stage.id] = (
                ProjectStageAccessOut(
                    stage_instance_id=stage.id,
                    stage=stage_value,
                    stage_label=_stage_label(stage_value),
                    sequence=stage.sequence,
                    access=access,
                    user_role_id=row.id,
                )
            )

    # ------------------------------------------------------------------
    # Project administrators
    # ------------------------------------------------------------------
    #
    # PROJECT_ADMIN remains project-scoped.
    #
    # Therefore a project admin has ADMIN access to every stage.
    # ------------------------------------------------------------------

    if stages:
        admin_result = await db.execute(
            select(
                UserRole.user_id,
                UserRole.id,
                User.email,
                User.first_name,
                User.last_name,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .join(
                User,
                User.id == UserRole.user_id,
            )
            .where(
                UserRole.scope_type == "PROJECT",
                UserRole.scope_id == project_id,
                UserRole.is_active == True,
                Role.name == "PROJECT_ADMIN",
                User.is_active == True,
            )
        )

        for row in admin_result.all():

            display_name = " ".join(
                part
                for part in (
                    row.first_name,
                    row.last_name,
                )
                if part
            ).strip()

            member = members_by_user.setdefault(
                row.user_id,
                {
                    "user_id": row.user_id,
                    "display_name": display_name or row.email,
                    "email": row.email,
                    "assignments": {},
                },
            )

            for stage in stages:

                stage_value = (
                    stage.stage.value
                    if hasattr(stage.stage, "value")
                    else str(stage.stage)
                )

                member["assignments"][stage.id] = (
                    ProjectStageAccessOut(
                        stage_instance_id=stage.id,
                        stage=stage_value,
                        stage_label=_stage_label(stage_value),
                        sequence=stage.sequence,
                        access="ADMIN",
                        user_role_id=row.id,
                    )
                )

    # ------------------------------------------------------------------
    # Project stage list
    # ------------------------------------------------------------------

    stage_outputs = []

    for stage in stages:

        stage_value = (
            stage.stage.value
            if hasattr(stage.stage, "value")
            else str(stage.stage)
        )

        stage_outputs.append(
            ProjectStageAccessOut(
                stage_instance_id=stage.id,
                stage=stage_value,
                stage_label=_stage_label(stage_value),
                sequence=stage.sequence,
                access="NONE",
            )
        )

    # ------------------------------------------------------------------
    # Member list
    # ------------------------------------------------------------------

    members = []

    for member in members_by_user.values():

        assignments = sorted(
            member["assignments"].values(),
            key=lambda item: (
                item.sequence,
                item.stage_label,
            ),
        )

        members.append(
            ProjectAccessMemberOut(
                user_id=member["user_id"],
                display_name=member["display_name"],
                email=member["email"],
                assignments=assignments,
            )
        )

    members.sort(
        key=lambda item: item.display_name.lower()
    )

    return ProjectAccessOut(
        project_id=project.id,
        project_name=project.project_name,
        stages=stage_outputs,
        members=members,
    )


async def update_user_stage_access(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    payload: UpdateUserStageAccessIn,
) -> ProjectAccessOut:
    """
    Replace the complete stage-access state for one user.

    Example:

        Design       -> EDIT
        Construction -> VIEW
        Business     -> omitted

    results in:

        Design       -> PROJECT_EDITOR
        Construction -> PROJECT_VIEWER
        Business     -> no active stage role

    The operation is performed inside the caller's transaction.
    """

    project = await _get_project_or_404(
        db,
        project_id,
    )

    project_class_value = (
        project.project_class.value
        if hasattr(project.project_class, "value")
        else str(project.project_class)
    )

    # ------------------------------------------------------------------
    # Validate target user
    # ------------------------------------------------------------------

    user_result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,
        )
    )

    user = user_result.scalars().first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive",
        )

    # ------------------------------------------------------------------
    # Load actual stages belonging to this project
    # ------------------------------------------------------------------

    stages = await _get_project_stages(
        db,
        project_id,
    )

    stage_map = {
        stage.id: stage
        for stage in stages
    }

    # ------------------------------------------------------------------
    # Determine which stages are currently enabled.
    #
    # Historical ProjectStageInstance rows are intentionally retained,
    # so existence of a stage instance does NOT mean the stage is active.
    #
    # RECURRING is always valid when its instance exists because it is
    # not represented by ProjectStageConfig.
    # ------------------------------------------------------------------

    config_result = await db.execute(
        select(
            ProjectStageConfig.stage,
            ProjectStageConfig.enabled,
        ).where(
            ProjectStageConfig.project_id == project_id,
        )
    )

    enabled_stage_names = {
        (
            stage.value
            if hasattr(stage, "value")
            else str(stage)
        )
        for stage, enabled in config_result.all()
        if enabled
    }

    enabled_stage_ids = set()

    for stage in stages:
        stage_value = (
            stage.stage.value
            if hasattr(stage.stage, "value")
            else str(stage.stage)
        )

        if stage_value == "RECURRING":
            if project_class_value == "RECURRING":
                enabled_stage_ids.add(stage.id)

        elif stage_value in enabled_stage_names:
            enabled_stage_ids.add(stage.id)

    # ------------------------------------------------------------------
    # Validate submitted assignments
    # ------------------------------------------------------------------

    requested: Dict[UUID, str] = {}

    for assignment in payload.assignments:

        if assignment.stage_instance_id not in stage_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stage {assignment.stage_instance_id} "
                    "does not belong to this project"
                ),
            )

        if assignment.stage_instance_id not in enabled_stage_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stage {assignment.stage_instance_id} "
                    "is disabled and cannot receive project access"
                ),
            )

        if assignment.stage_instance_id in requested:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Stage {assignment.stage_instance_id} "
                    "is specified more than once"
                ),
            )

        requested[
            assignment.stage_instance_id
        ] = assignment.access.value

    # ------------------------------------------------------------------
    # Resolve the two stage roles
    # ------------------------------------------------------------------

    role_result = await db.execute(
        select(Role).where(
            Role.name.in_(_STAGE_ROLE_NAMES)
        )
    )

    roles = {
        role.name: role
        for role in role_result.scalars().all()
    }

    missing_roles = (
        set(_STAGE_ROLE_NAMES)
        - set(roles)
    )

    if missing_roles:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Required stage roles are missing: "
                f"{sorted(missing_roles)}"
            ),
        )

    # ------------------------------------------------------------------
    # Load existing stage assignments
    # ------------------------------------------------------------------

    if stage_map:
        existing_result = await db.execute(
            select(
                UserRole,
                Role.name,
            )
            .join(
                Role,
                Role.id == UserRole.role_id,
            )
            .where(
                UserRole.user_id == user_id,
                UserRole.scope_type == "STAGE",
                UserRole.scope_id.in_(
                    list(stage_map)
                ),
                Role.name.in_(
                    _STAGE_ROLE_NAMES
                ),
            )
        )

        existing = {
            (user_role.scope_id, role_name): user_role
            for user_role, role_name
            in existing_result.all()
        }

    else:
        existing = {}

    # ------------------------------------------------------------------
    # Reconcile desired state
    # ------------------------------------------------------------------

    for stage_id in stage_map:

        requested_access = requested.get(
            stage_id
        )

        if requested_access == "EDIT":
            desired_role = "PROJECT_EDITOR"

        elif requested_access == "VIEW":
            desired_role = "PROJECT_VIEWER"

        else:
            desired_role = None

        current_editor = existing.get(
            (
                stage_id,
                "PROJECT_EDITOR",
            )
        )

        current_viewer = existing.get(
            (
                stage_id,
                "PROJECT_VIEWER",
            )
        )

        current_active_role = None

        if (
            current_editor is not None
            and current_editor.is_active
        ):
            current_active_role = "PROJECT_EDITOR"

        elif (
            current_viewer is not None
            and current_viewer.is_active
        ):
            current_active_role = "PROJECT_VIEWER"

        if current_active_role == desired_role:
            continue

        # Remove both possible active variants first.
        #
        # This also repairs malformed data where both roles happen
        # to be active for the same user/stage.
        for user_role in (
            current_editor,
            current_viewer,
        ):
            if (
                user_role is not None
                and user_role.is_active
            ):
                user_role.is_active = False
                db.add(user_role)

        # Add/reactivate requested role.
        if desired_role is not None:

            target = existing.get(
                (
                    stage_id,
                    desired_role,
                )
            )

            if target is not None:
                target.is_active = True
                db.add(target)

            else:
                db.add(
                    UserRole(
                        user_id=user_id,
                        role_id=roles[
                            desired_role
                        ].id,
                        scope_type="STAGE",
                        scope_id=stage_id,
                        is_active=True,
                    )
                )

    await db.flush()

    return await get_project_access(
        db,
        project_id,
    )


async def _get_stage_role_map(
    db: AsyncSession,
) -> dict[str, UUID]:
    """
    Return role name -> role ID for the stage-level project roles.
    """

    result = await db.execute(
        select(Role.id, Role.name).where(
            Role.name.in_(_STAGE_ROLE_NAMES),
            Role.is_active == True,
        )
    )

    return {
        role_name: role_id
        for role_id, role_name in result.all()
    }


async def assign_user_to_project_stages(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    role_name: str,
) -> None:
    """
    Assign one user to every currently existing stage in a project.

    Intended for project creation / legacy project-level access migration.

    role_name must be PROJECT_EDITOR or PROJECT_VIEWER.
    """

    if role_name not in _STAGE_ROLE_NAMES:
        raise ValueError(
            f"Invalid stage role: {role_name}"
        )

    stages_result = await db.execute(
        select(ProjectStageInstance.id)
        .outerjoin(
            ProjectStageConfig,
            ProjectStageConfig.project_id
            == ProjectStageInstance.project_id,
        )
        .where(
            ProjectStageInstance.project_id == project_id,
            or_(
                ProjectStageInstance.stage == ProjectStage.RECURRING,
                ProjectStageConfig.stage
                == ProjectStageInstance.stage,
            ),
            or_(
                ProjectStageInstance.stage == ProjectStage.RECURRING,
                ProjectStageConfig.enabled == True,
            ),
        )
    )

    stage_ids = list(
        stages_result.scalars().all()
    )

    if not stage_ids:
        return

    role_map = await _get_stage_role_map(db)

    role_id = role_map.get(role_name)

    if role_id is None:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Required role '{role_name}' "
                "does not exist"
            ),
        )

    # Fetch existing assignments for this user/project.
    existing_result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.scope_type == "STAGE",
            UserRole.scope_id.in_(stage_ids),
            UserRole.role_id == role_id,
        )
    )

    existing_by_stage = {
        role.scope_id: role
        for role in existing_result.scalars().all()
    }

    for stage_id in stage_ids:

        existing = existing_by_stage.get(
            stage_id
        )

        if existing is not None:
            existing.is_active = True
            db.add(existing)
            continue

        db.add(
            UserRole(
                user_id=user_id,
                role_id=role_id,
                scope_type="STAGE",
                scope_id=stage_id,
                is_active=True,
            )
        )


async def deactivate_user_project_stage_access(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
) -> None:
    """
    Remove all stage-level PROJECT_EDITOR / PROJECT_VIEWER
    assignments for one user in one project.
    """

    stage_result = await db.execute(
        select(ProjectStageInstance.id).where(
            ProjectStageInstance.project_id == project_id
        )
    )

    stage_ids = list(
        stage_result.scalars().all()
    )

    if not stage_ids:
        return

    role_result = await db.execute(
        select(Role.id).where(
            Role.name.in_(_STAGE_ROLE_NAMES)
        )
    )

    role_ids = list(
        role_result.scalars().all()
    )

    if not role_ids:
        return

    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.scope_type == "STAGE",
            UserRole.scope_id.in_(stage_ids),
            UserRole.role_id.in_(role_ids),
            UserRole.is_active == True,
        )
    )

    for user_role in result.scalars().all():
        user_role.is_active = False
        db.add(user_role)


async def deactivate_all_project_stage_access(
    db: AsyncSession,
    *,
    project_id: UUID,
) -> None:
    """
    Deactivate every PROJECT_EDITOR / PROJECT_VIEWER stage assignment
    belonging to a project.

    PROJECT_ADMIN assignments are deliberately untouched.
    """

    stage_result = await db.execute(
        select(ProjectStageInstance.id).where(
            ProjectStageInstance.project_id == project_id
        )
    )

    stage_ids = list(
        stage_result.scalars().all()
    )

    if not stage_ids:
        return

    role_result = await db.execute(
        select(Role.id).where(
            Role.name.in_(_STAGE_ROLE_NAMES)
        )
    )

    role_ids = list(
        role_result.scalars().all()
    )

    if not role_ids:
        return

    result = await db.execute(
        select(UserRole).where(
            UserRole.scope_type == "STAGE",
            UserRole.scope_id.in_(stage_ids),
            UserRole.role_id.in_(role_ids),
            UserRole.is_active == True,
        )
    )

    for user_role in result.scalars().all():
        user_role.is_active = False
        db.add(user_role)