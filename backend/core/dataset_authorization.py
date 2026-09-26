from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dataset_permissions import (
    ALL_BRANCHES,
    ORG_ONLY,
    READ_ONLY,
    SUPERADMIN_ONLY,
    get_dataset_category,
    is_registered_dataset_type,
    is_scope_allowed,
)
from core import rbac
from core.security import Principal, get_current_principal
from crud import dataset_revisions as dataset_revision_crud
from models.project import Project
from models.user_roles import UserRole
from models.roles import Role
from sqlalchemy import select
from core.session import get_session

async def get_effective_role_names(*args, **kwargs):
    """Indirection kept patchable for callers/tests while delegating to RBAC."""
    return await rbac.get_effective_role_names(*args, **kwargs)

async def get_org_scoped_role_names(*args, **kwargs):
    """Indirection kept patchable for callers/tests while delegating to RBAC."""
    return await rbac.get_org_scoped_role_names(*args, **kwargs)

async def get_dataset_revision(db: AsyncSession, revision_id: UUID):
    """Resolve a dataset revision through the CRUD layer."""
    return await dataset_revision_crud.get_dataset_revision(db, revision_id)


async def assert_revision_view_permission(
    db: AsyncSession,
    principal: Principal,
    revision,
) -> None:
    """Allow published revisions in the caller's hierarchy and drafts only to editors."""
    scope_type = (revision.scope_type or "DEFAULT").upper()
    scope_id = revision.scope_id
    user_id = principal.user_id

    if revision.status == "draft":
        if scope_type == "DEFAULT":
            roles = await get_effective_role_names(db, user_id)
            allowed = rbac.SUPER_ADMIN in _role_set(roles)
        elif scope_type == "ORG":
            roles = await get_org_scoped_role_names(db, user_id, scope_id)
            allowed = rbac.ORG_ADMIN in _role_set(roles)
        elif scope_type == "PROJECT":
            roles = await get_effective_role_names(db, user_id, project_id=scope_id)
            allowed = bool(_role_set(roles) & {rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR})
        else:
            allowed = False
    elif scope_type == "DEFAULT":
        allowed = True
    elif scope_type == "ORG":
        allowed = principal.organization_id == scope_id
        if not allowed:
            result = await db.execute(
                select(Project.id).join(
                    UserRole,
                    (UserRole.scope_id == Project.id)
                    & (UserRole.scope_type == rbac.PROJECT)
                    & (UserRole.user_id == user_id)
                    & (UserRole.is_active == True),
                ).where(
                    Project.proponent_org_id == scope_id,
                )
            )
            allowed = result.scalars().first() is not None
    elif scope_type == "PROJECT":
        result = await db.execute(
            select(UserRole.id).join(Role, Role.id == UserRole.role_id).where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                UserRole.scope_type == rbac.PROJECT,
                UserRole.scope_id == scope_id,
                Role.name.in_({rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR, rbac.PROJECT_VIEWER}),
            )
        )
        allowed = result.scalars().first() is not None
    else:
        allowed = False

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset revision not found",
        )


async def require_dataset_read_access(
    request: Request,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> None:
    """Authenticate dataset reads and authorize explicit revision selectors."""
    if request.method != "GET":
        return
    raw_ids = list(request.query_params.getlist("dataset_revision_id"))
    raw_ids.extend(request.query_params.getlist("dataset_revision_ids"))
    path_revision_id = request.path_params.get("revision_id")
    if path_revision_id:
        raw_ids.append(str(path_revision_id))
    row_ids = [value for key, value in request.path_params.items() if key.endswith("_id") and key != "revision_id"]
    if row_ids:
        endpoint = request.scope.get("route")
        endpoint_globals = getattr(getattr(endpoint, "endpoint", None), "__globals__", {})
        candidate_values = list(endpoint_globals.values())
        for candidate in tuple(candidate_values):
            if getattr(candidate, "__module__", "").startswith("crud."):
                candidate_values.extend(getattr(candidate, "__globals__", {}).values())
        for row_id in row_ids:
            try:
                parsed_id = UUID(str(row_id))
            except ValueError:
                continue
            seen_models = set()
            for model in candidate_values:
                if id(model) in seen_models:
                    continue
                seen_models.add(id(model))
                table = getattr(model, "__table__", None)
                if table is None or "dataset_revision_id" not in table.c or "id" not in table.c:
                    continue
                result = await db.execute(
                    select(model.dataset_revision_id).where(model.id == parsed_id)
                )
                revision_id = result.scalar_one_or_none()
                if revision_id:
                    revision_value = str(revision_id)
                    if raw_ids and revision_value not in raw_ids:
                        raise HTTPException(status_code=404, detail="Dataset record not found")
                    if revision_value not in raw_ids:
                        raw_ids.append(revision_value)
                    break
        # If the shared session cannot resolve the row (for example, a legacy
        # CRUD adapter or an endpoint test double owns the lookup), let the
        # handler perform its normal not-found lookup. In production, mapped
        # revisioned rows are authorized here before the handler returns them.
    if not raw_ids and not row_ids:
        endpoint_name = getattr(getattr(request.scope.get("route"), "endpoint", None), "__name__", "")
        if endpoint_name not in {
            "get_operational_equipment_list",
            "get_active_maintenance_replacement_factors",
        }:
            raise HTTPException(
                status_code=400,
                detail="dataset_revision_id is required when reading revisioned dataset data",
            )
        project_id = request.query_params.get("project_id")
        if project_id:
            try:
                parsed_project_id = UUID(project_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid project ID")
            from crud.project_dataset_revisions import list_project_dataset_revisions_by_project

            bindings = await list_project_dataset_revisions_by_project(db, parsed_project_id)
            if bindings:
                raw_ids.append(str(bindings[0].dataset_revision_id))
        if not raw_ids:
            from crud.dataset_revisions import get_published_dataset_revision

            default_revision = await get_published_dataset_revision(db)
            if default_revision:
                raw_ids.append(str(default_revision.id))
        if not raw_ids:
            raise HTTPException(status_code=404, detail="Published default dataset revision not found")
    for raw_id in set(raw_ids):
        try:
            revision_id = UUID(raw_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid dataset revision ID")
        revision = await get_dataset_revision(db, revision_id)
        if not revision:
            raise HTTPException(status_code=404, detail="Dataset revision not found")
        await assert_revision_view_permission(db, principal, revision)


def protect_dataset_reads(router) -> None:
    """Add shared auth/read checks before a dataset router is included by the app."""
    dependency = Depends(require_dataset_read_access)
    for route in router.routes:
        if hasattr(route, "dependencies"):
            route.dependencies.append(dependency)

def _role_set(roles) -> set:
    """Normalise RBAC results so list/set implementations are both supported."""
    return set(roles or ())

async def assert_revision_edit_permission(
    db: AsyncSession,
    principal: Principal,
    dataset_revision_id: Optional[UUID] = None,
    dataset_type: Optional[str] = None,
) -> None:
    """
    Validate that the current principal has permission to create, update, or delete
    records in the given dataset and dataset revision.

    Enforces:
      1. READ_ONLY datasets are immutable.
      2. Dataset governance category vs. revision scope tier (ALL_BRANCHES, ORG_ONLY, SUPERADMIN_ONLY).
      3. Dataset revision must be in 'draft' status.
      4. Caller role matching the scope tier:
         - DEFAULT branch: SUPER_ADMIN
         - ORG branch: ORG_ADMIN (or SUPER_ADMIN) scoped to revision.scope_id
         - PROJECT branch: PROJECT_ADMIN or PROJECT_EDITOR (or SUPER_ADMIN) scoped to revision.scope_id
      5. Fallback for non-revisioned datasets based on dataset governance category.
    """
    if dataset_type:
        if not is_registered_dataset_type(dataset_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Dataset '{dataset_type}' has no registered governance category",
            )
        category = get_dataset_category(dataset_type)
        if category == READ_ONLY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Dataset '{dataset_type}' is read-only and cannot be modified",
            )

    if dataset_revision_id is not None:
        revision = await get_dataset_revision(db, dataset_revision_id)
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset revision not found",
            )

        if revision.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot modify records in a '{revision.status}' dataset revision (only 'draft' revisions can be edited)",
            )

        scope_type = (revision.scope_type or "DEFAULT").upper()
        if dataset_type and not is_scope_allowed(dataset_type, scope_type):
            cat = get_dataset_category(dataset_type)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Dataset '{dataset_type}' has restriction level '{cat}' and cannot be modified in a '{scope_type}' revision",
            )

        uid = principal.user_id

        if scope_type == "DEFAULT":
            roles = await get_effective_role_names(db, uid)
            if rbac.SUPER_ADMIN not in _role_set(roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Super Admin may modify Default branch datasets",
                )

        elif scope_type == "ORG":
            if not revision.scope_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ORG dataset revision is missing a scope_id (organisation ID)",
                )

            org_roles = await get_org_scoped_role_names(db, uid, revision.scope_id)
            org_role_set = _role_set(org_roles)
            if rbac.ORG_ADMIN not in org_role_set:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Organisation Admin or Super Admin may modify Organisation branch datasets",
                )

        elif scope_type == "PROJECT":
            if not revision.scope_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PROJECT dataset revision is missing a scope_id (project ID)",
                )

            proj_roles = await get_effective_role_names(
                db, uid, project_id=revision.scope_id
            )
            allowed = {
                rbac.PROJECT_ADMIN,
                rbac.PROJECT_EDITOR,
            }

            if not _role_set(proj_roles).intersection(allowed):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Project Admin, Project Editor, or Super Admin may modify Project branch datasets",
                )

        return

    # Non-revisioned dataset fallback
    roles = await get_effective_role_names(db, principal.user_id)
    role_set = _role_set(roles)

    cat = (get_dataset_category(dataset_type) if dataset_type else SUPERADMIN_ONLY)

    if cat == SUPERADMIN_ONLY or cat == READ_ONLY:
        if rbac.SUPER_ADMIN not in role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin may modify this dataset",
            )
    elif cat == ORG_ONLY:
        if (rbac.ORG_ADMIN not in role_set and rbac.SUPER_ADMIN not in role_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organisation Admin or Super Admin may modify this dataset",
            )
    elif cat == ALL_BRANCHES:
        allowed = {rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR, rbac.ORG_ADMIN, rbac.SUPER_ADMIN}
        if not role_set.intersection(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this dataset",
            )
