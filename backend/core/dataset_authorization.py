from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
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
from models.dataset_revisions import DatasetRevision


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
        result = await db.execute(
            select(DatasetRevision).where(DatasetRevision.id == dataset_revision_id)
        )
        revision = result.scalars().first()
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
            roles = await rbac.get_effective_role_names(db, uid)
            if rbac.SUPER_ADMIN not in roles:
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
            org_roles = await rbac.get_org_scoped_role_names(db, uid, revision.scope_id)
            if rbac.ORG_ADMIN not in org_roles and rbac.SUPER_ADMIN not in org_roles:
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
            proj_roles = await rbac.get_effective_role_names(db, uid, project_id=revision.scope_id)
            allowed = {rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR, rbac.SUPER_ADMIN}
            if not proj_roles.intersection(allowed):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Project Admin, Project Editor, or Super Admin may modify Project branch datasets",
                )
        return

    # Non-revisioned dataset fallback
    roles = await rbac.get_effective_role_names(db, principal.user_id)
    cat = get_dataset_category(dataset_type) if dataset_type else SUPERADMIN_ONLY
    if cat == SUPERADMIN_ONLY or cat == READ_ONLY:
        if rbac.SUPER_ADMIN not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin may modify this dataset",
            )
    elif cat == ORG_ONLY:
        if rbac.ORG_ADMIN not in roles and rbac.SUPER_ADMIN not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organisation Admin or Super Admin may modify this dataset",
            )
    elif cat == ALL_BRANCHES:
        allowed = {rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR, rbac.ORG_ADMIN, rbac.SUPER_ADMIN}
        if not roles.intersection(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this dataset",
            )
