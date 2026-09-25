

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.access_context import DatasetVisibility, get_dataset_visibility_context
from core.rbac import (
    get_effective_role_names,
    get_org_scoped_role_names,
    get_any_project_role_names,
    get_all_role_names_for_ui,
    get_stage_access_level,
    SUPER_ADMIN,
    ORG_ADMIN,
    PROJECT_ADMIN,
)
from core.authorization_policy import access_name
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.project import list_projects_for_org, list_projects_for_user_roles
from schemas.project import ProjectOut

router = APIRouter(prefix="/api/me", tags=["me"])


class MeProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    email: str
    organisation_id: Optional[UUID] = None
    organisation_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


class MeStageAccess(BaseModel):
    stage_instance_id: UUID
    stage: str
    stage_label: str
    sequence: int = 0
    access: str


class MeAccess(BaseModel):
    user_id: UUID
    project_id: Optional[UUID]
    effective_roles: List[str]
    stage_access: List[MeStageAccess] = Field(default_factory=list)


class MeDatasetTier(BaseModel):
    user_id: UUID
    project_id: Optional[UUID]
    dataset_visibility: DatasetVisibility



@router.get("", response_model=MeProfile)
async def get_my_profile(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    from models.users import User
    from models.organizations import Organization
    from sqlalchemy.orm import outerjoin

    result = await db.execute(
        select(
            User.first_name,
            User.last_name,
            User.username,
            Organization.name.label("org_name"),
        )
        .select_from(User)
        .outerjoin(Organization, Organization.id == User.organization_id)
        .where(User.id == principal.user_id)
    )
    row = result.first()
    return MeProfile(
        user_id=principal.user_id,
        email=principal.email,
        organisation_id=principal.organization_id,
        organisation_name=row.org_name if row else None,
        first_name=row.first_name if row else None,
        last_name=row.last_name if row else None,
        username=row.username if row else None,
    )


@router.get("/access", response_model=MeAccess)
async def get_my_access(
    project_id: Optional[UUID] = Query(None, description="Project context for scoped role lookup"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):

    stage_access: List[MeStageAccess] = []

    if project_id:
        roles = await get_effective_role_names(
            db,
            principal.user_id,
            project_id=project_id,
        )

        from models.project_stage_instances import ProjectStageInstance

        stage_result = await db.execute(
            select(ProjectStageInstance)
            .where(ProjectStageInstance.project_id == project_id)
            .order_by(ProjectStageInstance.sequence, ProjectStageInstance.id)
        )

        stage_label_map = {
            "BUSINESS_CASE": "Business Case",
            "DESIGN": "Design",
            "CONSTRUCTION": "Construction",
            "RECURRING": "Recurring",
        }

        for stage_instance in stage_result.scalars().all():
            access = await get_stage_access_level(
                db=db,
                user_id=principal.user_id,
                project_id=project_id,
                stage_instance_id=stage_instance.id,
            )
            stage_value = (
                stage_instance.stage.value
                if hasattr(stage_instance.stage, "value")
                else str(stage_instance.stage)
            )
            stage_access.append(
                MeStageAccess(
                    stage_instance_id=stage_instance.id,
                    stage=stage_value,
                    stage_label=stage_label_map.get(stage_value, stage_value),
                    sequence=stage_instance.sequence,
                    access=access_name(access),
                )
            )
    else:
        roles = await get_all_role_names_for_ui(
            db, principal.user_id, principal.organization_id
        )

    return MeAccess(
        user_id=principal.user_id,
        project_id=project_id,
        effective_roles=sorted(roles),
        stage_access=stage_access,
    )


@router.get("/dataset-tier", response_model=MeDatasetTier)
async def get_my_dataset_tier(
    project_id: Optional[UUID] = Query(None, description="Project context"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    tier = await get_dataset_visibility_context(principal, db, project_id=project_id)
    return MeDatasetTier(
        user_id=principal.user_id,
        project_id=project_id,
        dataset_visibility=tier,
    )


@router.get("/projects", response_model=List[ProjectOut])
async def get_my_projects(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):

    if principal.organization_id is not None:
        roles = await get_org_scoped_role_names(db, principal.user_id, principal.organization_id)
    else:
        roles = await get_effective_role_names(db, principal.user_id)

    if "ORG_ADMIN" in roles and principal.organization_id is not None:
        return await list_projects_for_org(db, principal.organization_id)

    return await list_projects_for_user_roles(db, principal.user_id)


class PendingActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: UUID
    project_name: str
    stage_instance_id: UUID
    stage: str
    report_number: int
    num_reports_required: int = 1
    approval_status: str


@router.get("/pending-actions", response_model=List[PendingActionOut])
async def get_pending_actions(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    from models.user_roles import UserRole
    from models.roles import Role
    from models.project import Project
    from models.project_options import ProjectOption
    from models.project_stage_instances import ProjectStageInstance
    from sqlalchemy import distinct, func as sqlfunc

    PENDING_STATUSES = ("submitted", "pending_reopen")

    if principal.organization_id is not None:
        org_roles = await get_org_scoped_role_names(db, principal.user_id, principal.organization_id)
    else:
        org_roles = await get_effective_role_names(db, principal.user_id)

    is_org_or_super_admin = bool({SUPER_ADMIN, ORG_ADMIN} & org_roles)

    if is_org_or_super_admin and principal.organization_id is not None:
        q = (
            select(
                Project.id.label("project_id"),
                Project.project_name.label("project_name"),
                ProjectStageInstance.id.label("stage_instance_id"),
                ProjectStageInstance.stage.label("stage"),
                ProjectOption.report_number.label("report_number"),
                sqlfunc.coalesce(ProjectStageInstance.num_reports_required, 1).label("num_reports_required"),
                ProjectOption.approval_status.label("approval_status"),
            )
            .select_from(ProjectOption)
            .join(ProjectStageInstance, ProjectStageInstance.id == ProjectOption.stage_instance_id)
            .join(Project, Project.id == ProjectOption.project_id)
            .where(
                ProjectOption.approval_status.in_(PENDING_STATUSES),
                Project.proponent_org_id == principal.organization_id,
            )
            .distinct(
                ProjectOption.stage_instance_id,
                ProjectOption.report_number,
            )
            .order_by(
                ProjectOption.stage_instance_id,
                ProjectOption.report_number,
            )
        )
    else:
        admin_project_ids_subq = (
            select(UserRole.scope_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == principal.user_id,
                UserRole.is_active == True,
                UserRole.scope_type == "PROJECT",
                Role.name == PROJECT_ADMIN,
            )
            .scalar_subquery()
        )
        q = (
            select(
                Project.id.label("project_id"),
                Project.project_name.label("project_name"),
                ProjectStageInstance.id.label("stage_instance_id"),
                ProjectStageInstance.stage.label("stage"),
                ProjectOption.report_number.label("report_number"),
                sqlfunc.coalesce(ProjectStageInstance.num_reports_required, 1).label("num_reports_required"),
                ProjectOption.approval_status.label("approval_status"),
            )
            .select_from(ProjectOption)
            .join(ProjectStageInstance, ProjectStageInstance.id == ProjectOption.stage_instance_id)
            .join(Project, Project.id == ProjectOption.project_id)
            .where(
                ProjectOption.approval_status.in_(PENDING_STATUSES),
                ProjectOption.project_id.in_(admin_project_ids_subq),
            )
            .distinct(
                ProjectOption.stage_instance_id,
                ProjectOption.report_number,
            )
            .order_by(
                ProjectOption.stage_instance_id,
                ProjectOption.report_number,
            )
        )

    result = await db.execute(q)
    rows = result.mappings().all()
    return [PendingActionOut(**dict(r)) for r in rows]
