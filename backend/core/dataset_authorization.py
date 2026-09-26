from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dataset_permissions import (
    ALL_BRANCHES,
    ORG_ONLY,
    READ_ONLY,
    SUPERADMIN_ONLY,
    get_dataset_category,
    is_scope_allowed,
)
from core import rbac
from core.security import Principal
from crud import dataset_revisions as dataset_revision_crud

async def get_effective_role_names(*args, **kwargs):
    """Indirection kept patchable for callers/tests while delegating to RBAC."""
    return await rbac.get_effective_role_names(*args, **kwargs)

async def get_org_scoped_role_names(*args, **kwargs):
    """Indirection kept patchable for callers/tests while delegating to RBAC."""
    return await rbac.get_org_scoped_role_names(*args, **kwargs)

async def get_dataset_revision(db: AsyncSession, revision_id: UUID):
    """Resolve a dataset revision through the CRUD layer."""
    return await dataset_revision_crud.get_dataset_revision(db, revision_id)

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
            if (
                rbac.ORG_ADMIN not in org_role_set
                and rbac.SUPER_ADMIN not in org_role_set
            ):
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
                rbac.SUPER_ADMIN,
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
