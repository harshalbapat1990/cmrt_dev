from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_principal, Principal
from core.session import get_session
from core.rbac import require_stage_access
from core.authorization_policy import AccessLevel
# from core.rbac import get_effective_role_names, SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR
from crud.audit_logs import write_audit_event
from crud.project_mitigations import (
    create_project_mitigation,
    delete_project_mitigation,
    get_project_mitigation,
    list_project_mitigations,
    update_project_mitigation,
)
from crud.project_stage_instances import get_project_stage_instance
from schemas.project_mitigations import (
    ProjectMitigationCreate,
    ProjectMitigationOut,
    ProjectMitigationUpdate,
)

router = APIRouter(prefix="/api/project-mitigations", tags=["project-mitigations"])

# _EDITOR_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR}


# async def _require_editor(db: AsyncSession, principal: Principal, project_id: UUID) -> None:
#     roles = await get_effective_role_names(db, principal.user_id, project_id)
#     if not roles.intersection(_EDITOR_ROLES):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You do not have permission to modify mitigations for this project.",
#         )


def _assert_stage_not_locked(stage_instance) -> None:
    if stage_instance and stage_instance.approval_status == "final_approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This stage is final-approved and cannot be edited.",
        )


@router.get("", response_model=List[ProjectMitigationOut])
async def list_mitigations(
    project_stage_instance_id: UUID = Query(...),
    project_option_id: Optional[UUID] = Query(None),
    submission_stage: Optional[str] = Query(None, description="Design | Construction"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    stage_instance = await get_project_stage_instance(db, project_stage_instance_id)
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.VIEW,
    )
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")
    rows = await list_project_mitigations(
        db, project_stage_instance_id, project_option_id, submission_stage
    )
    return [ProjectMitigationOut.model_validate(r) for r in rows]


def _reject_users_lifecycle_with_construction_submission(
    lifecycle_phase: str,
    submission_stage: str,
) -> None:
    lc = (lifecycle_phase or "").strip().lower()
    sub = (submission_stage or "").strip().lower()
    if lc == "users" and sub == "construction":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users lifecycle mitigations are only allowed when submission stage is Design.",
        )


@router.post("", response_model=ProjectMitigationOut, status_code=status.HTTP_201_CREATED)
async def create_mitigation(
    body: ProjectMitigationCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    stage_instance = await get_project_stage_instance(db, body.project_stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")
    if stage_instance.project_id != body.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id does not match stage instance.")
    await require_stage_access(
        db,
        principal,
        body.project_id,
        stage_instance.id,
        AccessLevel.EDIT,
    )
    _assert_stage_not_locked(stage_instance)

    _reject_users_lifecycle_with_construction_submission(
            body.lifecycle_phase,
            body.submission_stage,
        )

    obj = await create_project_mitigation(db, body.model_dump())
    await write_audit_event(
        db,
        entity_type="project_mitigation",
        entity_id=obj.id,
        action="CREATE",
        entity_name="Mitigation",
        metadata={
            "project_id": str(body.project_id),
            "stage": stage_instance.stage.value,
            "stage_instance_id": str(stage_instance.id),
        },
    )
    await db.commit()
    await db.refresh(obj)
    return ProjectMitigationOut.model_validate(obj)


@router.patch("/{mitigation_id}", response_model=ProjectMitigationOut)
async def patch_mitigation(
    mitigation_id: UUID,
    body: ProjectMitigationUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_project_mitigation(db, mitigation_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mitigation not found.")
    stage_instance = await get_project_stage_instance(db, obj.project_stage_instance_id)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        stage_instance.id,
        AccessLevel.EDIT,
    )
    _assert_stage_not_locked(stage_instance)

    patch = body.model_dump(exclude_unset=True)
    if "lifecycle_phase" in patch and patch["lifecycle_phase"] is not None:
        _reject_users_lifecycle_with_construction_submission(
            patch["lifecycle_phase"],
            obj.submission_stage,
        )
    updated = await update_project_mitigation(db, mitigation_id, patch)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mitigation not found.")
    await write_audit_event(
        db,
        entity_type="project_mitigation",
        entity_id=mitigation_id,
        action="UPDATE",
        entity_name="Mitigation",
        metadata={
            "project_id": str(obj.project_id),
            "stage": stage_instance.stage.value,
            "stage_instance_id": str(stage_instance.id),
        },
    )
    await db.commit()
    await db.refresh(updated)
    return ProjectMitigationOut.model_validate(updated)


@router.delete("/{mitigation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mitigation(
    mitigation_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_project_mitigation(db, mitigation_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mitigation not found.")
    stage_instance = await get_project_stage_instance(db, obj.project_stage_instance_id)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        stage_instance.id,
        AccessLevel.EDIT,
    )
    _assert_stage_not_locked(stage_instance)

    ok = await delete_project_mitigation(db, mitigation_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mitigation not found.")
    await write_audit_event(
        db,
        entity_type="project_mitigation",
        entity_id=mitigation_id,
        action="DELETE",
        entity_name="Mitigation",
        metadata={
            "project_id": str(obj.project_id),
            "stage": stage_instance.stage.value,
            "stage_instance_id": str(stage_instance.id),
        },
    )
    await db.commit()