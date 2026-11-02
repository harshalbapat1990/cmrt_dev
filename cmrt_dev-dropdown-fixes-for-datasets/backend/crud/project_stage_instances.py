from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from models.project_stage_instances import ProjectStageInstance
from schemas.project_stage_instances import ProjectStageInstanceCreate


async def create_project_stage_instance(
    db: AsyncSession, payload: ProjectStageInstanceCreate
) -> ProjectStageInstance:
    obj = ProjectStageInstance(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def list_project_stage_instances(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    awaiting_action: bool = False,
    user_id: Optional[UUID] = None,
) -> List[ProjectStageInstance]:
    """
    List project stage instances visible to a user.

    If user_id is supplied, only stages for which the user has
    project/stage access are returned.

    Project access rules:

        PROJECT_ADMIN
            -> all stages in the project

        PROJECT_EDITOR
            -> only explicitly assigned stages

        PROJECT_VIEWER
            -> only explicitly assigned stages

        ORG_ADMIN
            -> all stages belonging to projects in the user's
               organisation

        SUPER_ADMIN
            -> does not automatically receive project/stage access

    If user_id is None, no authorization filtering is applied.
    This is intended only for internal callers that already enforce
    authorization separately.
    """

    from sqlalchemy import and_, or_

    from models.user_roles import UserRole
    from models.roles import Role
    from models.project import Project

    query = (
        select(ProjectStageInstance)
        .options(joinedload(ProjectStageInstance.project))
    )

    if project_id:
        query = query.where(
            ProjectStageInstance.project_id == project_id
        )

    if awaiting_action:
        query = query.where(
            ProjectStageInstance.approval_status.in_(
                ("submitted", "pending_reopen")
            )
        )

    if user_id is not None:
        project_admin_exists = (
            select(1)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                UserRole.scope_type == "PROJECT",
                UserRole.scope_id == ProjectStageInstance.project_id,
                Role.name == "PROJECT_ADMIN",
            )
            .exists()
        )

        org_admin_exists = (
            select(1)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .join(
                Project,
                Project.proponent_org_id == UserRole.scope_id,
            )
            .where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                UserRole.scope_type == "ORGANISATION",
                Role.name == "ORG_ADMIN",
                Project.id == ProjectStageInstance.project_id,
            )
            .exists()
        )

        stage_access_exists = (
            select(1)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                UserRole.scope_type == "STAGE",
                UserRole.scope_id == ProjectStageInstance.id,
                Role.name.in_(
                    (
                        "PROJECT_EDITOR",
                        "PROJECT_VIEWER",
                    )
                ),
            )
            .exists()
        )

        query = query.where(
            or_(
                project_admin_exists,
                org_admin_exists,
                stage_access_exists,
            )
        )

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)

    return result.scalars().all()


async def list_pending_stages(
    db: AsyncSession,
    project_id: Optional[UUID] = None,
) -> List[ProjectStageInstance]:
    query = select(ProjectStageInstance).where(
        ProjectStageInstance.approval_status.in_(("submitted", "pending_reopen"))
    )
    if project_id:
        query = query.where(ProjectStageInstance.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_project_stage_instance(
    db: AsyncSession, instance_id: UUID
) -> Optional[ProjectStageInstance]:
    query = select(ProjectStageInstance).where(ProjectStageInstance.id == instance_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_project_stage_instance_by_project_and_stage(
    db: AsyncSession,
    project_id: UUID,
    stage: str,
) -> Optional[ProjectStageInstance]:
    stage_value = (
        stage.value
        if hasattr(stage, "value")
        else str(stage)
    )
    result = await db.execute(
        select(ProjectStageInstance).where(
            ProjectStageInstance.project_id == project_id,
            ProjectStageInstance.stage == stage_value,
        )
    )
    return result.scalars().first()


async def set_stage_approval_status(
    db: AsyncSession,
    obj: ProjectStageInstance,
    new_status: str,
    approved_by: Optional[UUID] = None,
    submitted_by: Optional[UUID] = None,
    justification: Optional[str] = None,
) -> ProjectStageInstance:
    obj.approval_status = new_status

    if new_status == "submitted":
        obj.submitted_by = submitted_by
        obj.submitted_at = datetime.utcnow()
        obj.current_justification = None

    elif new_status == "tech_approved":
        obj.technical_approved_at = datetime.utcnow()
        obj.approved_by = approved_by

    elif new_status == "final_approved":
        obj.approved_by = approved_by
        obj.approved_at = datetime.utcnow()
        obj.current_justification = None

    elif new_status == "rejected":
        obj.current_justification = justification

    elif new_status == "pending_reopen":
        if justification is not None:
            obj.current_justification = justification

    elif new_status == "draft":
        obj.approved_by = None
        obj.approved_at = None
        obj.technical_approved_at = None
        obj.current_justification = None

    obj.updated_on = datetime.utcnow()
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj