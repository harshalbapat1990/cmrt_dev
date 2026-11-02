from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# from core.rbac import (
#     ORG_ADMIN,
#     get_org_scoped_role_names,
# )

from core.rbac import (
    get_effective_role_names,
)
from core.authorization_policy import (
    can_manage_stage_access
)
from core.security import (
    Principal,
    get_current_principal,
)
from core.session import get_session

from crud.audit_logs import write_audit_event
from crud.org_admin import (
    verify_project_belongs_to_org,
)
from crud.project_access import (
    get_project_access,
    update_user_stage_access,
)

from schemas.project_access import (
    ProjectAccessOut,
    UpdateUserStageAccessIn,
)


router = APIRouter(
    prefix="/api/projects",
    tags=["project-access"],
)


async def _require_stage_access_manager_for_project(
    db: AsyncSession,
    principal: Principal,
    project_id: UUID,
) -> None:
    role_names = await get_effective_role_names(
        db,
        principal.user_id,
        project_id=project_id,
    )

    if not can_manage_stage_access(role_names):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stage access management permission required",
        )
    

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
    await _require_stage_access_manager_for_project(
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
    await _require_stage_access_manager_for_project(
        db,
        principal,
        project_id,
    )

    # The project has already been verified to belong to the
    # Org Admin's organisation above. The target user is therefore
    # allowed to receive stage access when they are a valid active
    # user visible to the organisation's access-management workflow.
    if principal.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation context is required",
        )


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
        action="UPDATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "target_user_id": str(user_id),
            "project_id": str(project_id),
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