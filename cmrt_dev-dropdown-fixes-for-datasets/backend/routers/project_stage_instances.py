
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
# from core.rbac import (
#     get_effective_role_names,
#     SUPER_ADMIN,
#     ORG_ADMIN,
#     PROJECT_ADMIN,
#     PROJECT_EDITOR,
# )
from core.rbac import (
    require_stage_access,
)
from core.authorization_policy import AccessLevel
from schemas.project_stage_instances import (
    ProjectStageInstanceCreate,
    ProjectStageInstanceOut,
)
from schemas.stage_approval_events import StageApprovalEventOut
from crud.project_stage_instances import (
    create_project_stage_instance,
    list_project_stage_instances,
    get_project_stage_instance,
    set_stage_approval_status,
    get_project_stage_instance_by_project_and_stage,
)
from crud.stage_approval_events import record_event, list_events_for_stage
from crud.audit_logs import write_audit_event
from crud.project import touch_project

from core.rbac import get_effective_role_names


router = APIRouter(prefix="/api/project-stage-instances", tags=["project-stage-instances"])

# ADMIN_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN}
# EDITOR_OR_ABOVE = {SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR}
# EDITOR_ONLY = {SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR}


# async def _require_roles(
#     db: AsyncSession,
#     principal: Principal,
#     project_id: UUID,
#     allowed: set,
#     detail: str = "Insufficient permissions",
# ) -> None:
#     roles = await get_effective_role_names(db, principal.user_id, project_id)
#     if not roles.intersection(allowed):
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def _get_instance_or_404(db: AsyncSession, instance_id: UUID):
    obj = await get_project_stage_instance(db, instance_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found")
    return obj


@router.post("", response_model=ProjectStageInstanceOut, status_code=status.HTTP_201_CREATED)
async def create_new_project_stage_instance(
    payload: ProjectStageInstanceCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    roles = await get_effective_role_names(
            db,
            principal.user_id,
            project_id=payload.project_id,
        )

    if not roles.intersection({"ORG_ADMIN", "PROJECT_ADMIN"}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project administration access required",
        )
    obj = await create_project_stage_instance(db, payload)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.get("", response_model=List[ProjectStageInstanceOut])
async def get_project_stage_instances(
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    awaiting_action: bool = Query(False, description="Only return stages awaiting admin action"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    instances = await list_project_stage_instances(
        db, 
        skip, 
        limit, 
        project_id, 
        awaiting_action,
        user_id=principal.user_id
    )
    return instances


@router.get("/{instance_id}", response_model=ProjectStageInstanceOut)
async def get_project_stage_instance_by_id(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)

    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.VIEW
    )
    return obj



@router.post("/{instance_id}/submit", response_model=ProjectStageInstanceOut)
async def submit_stage(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    await require_stage_access(
        db, 
        principal, 
        obj.project_id, 
        obj.id, 
        AccessLevel.EDIT
        )
    # await _require_roles(db, principal, obj.project_id, EDITOR_ONLY)

    if obj.approval_status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'draft' or 'rejected' to submit (currently '{obj.approval_status}')",
        )

    from_status = obj.approval_status
    obj = await set_stage_approval_status(db, obj, "submitted", submitted_by=principal.user_id)
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="submitted",
        performed_by=principal.user_id,
        from_status=from_status,
        to_status="submitted",
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="SUBMIT",
        performed_by=principal.user_id,
        new_value="submitted",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/request-reopen", response_model=ProjectStageInstanceOut)
async def request_reopen(
    instance_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.EDIT
    )
    # await _require_roles(db, principal, obj.project_id, EDITOR_OR_ABOVE)

    if obj.approval_status not in ("final_approved", "submitted"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot request reopen from status '{obj.approval_status}'",
        )

    from_status = obj.approval_status
    obj = await set_stage_approval_status(db, obj, "pending_reopen", justification=justification)
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="reopen_requested",
        performed_by=principal.user_id,
        from_status=from_status,
        to_status="pending_reopen",
        justification=justification,
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="REQUEST_REOPEN",
        performed_by=principal.user_id,
        old_value=from_status,
        new_value="pending_reopen",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/approve", response_model=ProjectStageInstanceOut)
async def approve_stage(
    instance_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'submitted' to approve (currently '{obj.approval_status}')",
        )

    obj = await set_stage_approval_status(db, obj, "final_approved", approved_by=principal.user_id)
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="approved",
        performed_by=principal.user_id,
        from_status="submitted",
        to_status="final_approved",
        justification=justification,
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="APPROVE",
        performed_by=principal.user_id,
        new_value="final_approved",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/reject", response_model=ProjectStageInstanceOut)
async def reject_stage(
    instance_id: UUID,
    justification: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if not justification or not justification.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Justification is required when rejecting a stage",
        )
    if obj.approval_status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'submitted' to reject (currently '{obj.approval_status}')",
        )

    obj = await set_stage_approval_status(db, obj, "rejected", justification=justification.strip())
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="rejected",
        performed_by=principal.user_id,
        from_status="submitted",
        to_status="rejected",
        justification=justification.strip(),
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="REJECT",
        performed_by=principal.user_id,
        new_value="rejected",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/approve-reopen", response_model=ProjectStageInstanceOut)
async def approve_reopen(
    instance_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status != "pending_reopen":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'pending_reopen' (currently '{obj.approval_status}')",
        )

    obj = await set_stage_approval_status(db, obj, "draft")
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="reopen_approved",
        performed_by=principal.user_id,
        from_status="pending_reopen",
        to_status="draft",
        justification=justification,
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="APPROVE_REOPEN",
        performed_by=principal.user_id,
        new_value="draft",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/reject-reopen", response_model=ProjectStageInstanceOut)
async def reject_reopen(
    instance_id: UUID,
    justification: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if not justification or not justification.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Justification is required when rejecting a reopen request",
        )
    if obj.approval_status != "pending_reopen":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'pending_reopen' (currently '{obj.approval_status}')",
        )

    obj = await set_stage_approval_status(db, obj, "final_approved", approved_by=principal.user_id)
    await record_event(
        db,
        stage_instance_id=obj.id,
        project_id=obj.project_id,
        event_type="reopen_rejected",
        performed_by=principal.user_id,
        from_status="pending_reopen",
        to_status="final_approved",
        justification=justification.strip(),
    )
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="REJECT_REOPEN",
        performed_by=principal.user_id,
        new_value="final_approved",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.get("/{instance_id}/events", response_model=List[StageApprovalEventOut])
async def get_stage_events(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)

    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.VIEW
    )

    events = await list_events_for_stage(db, obj.id)
    return events


@router.post("/{instance_id}/mark-in-review", response_model=ProjectStageInstanceOut)
async def mark_in_review(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'submitted' to mark in review (currently '{obj.approval_status}')",
        )
    obj = await set_stage_approval_status(db, obj, "in_review")
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="MARK_IN_REVIEW",
        performed_by=principal.user_id,
        new_value="in_review",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/technical-approve", response_model=ProjectStageInstanceOut)
async def technical_approve_stage(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status not in ("draft", "submitted", "in_review"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot tech approve from '{obj.approval_status}'",
        )
    obj = await set_stage_approval_status(db, obj, "tech_approved", approved_by=principal.user_id)
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="TECHNICAL_APPROVE",
        performed_by=principal.user_id,
        new_value="tech_approved",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/final-approve", response_model=ProjectStageInstanceOut)
async def final_approve_stage(
    instance_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status not in ("tech_approved", "submitted"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage must be 'tech_approved' or 'submitted' for final approval (currently '{obj.approval_status}')",
        )
    obj = await set_stage_approval_status(db, obj, "final_approved", approved_by=principal.user_id)
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="FINAL_APPROVE",
        performed_by=principal.user_id,
        new_value="final_approved",
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)


@router.post("/{instance_id}/reopen", response_model=ProjectStageInstanceOut)
async def reopen_stage(
    instance_id: UUID,
    reason: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await _get_instance_or_404(db, instance_id)
    # await _require_roles(db, principal, obj.project_id, ADMIN_ROLES)
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.id,
        AccessLevel.ADMIN
    )

    if obj.approval_status == "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stage is already draft")

    prev_status = obj.approval_status
    obj = await set_stage_approval_status(db, obj, "draft")
    await write_audit_event(
        db,
        entity_type="stage_instance",
        entity_id=obj.id,
        action="REOPEN",
        performed_by=principal.user_id,
        old_value=prev_status,
        new_value="draft",
        metadata={"reason": reason} if reason else None,
    )
    await touch_project(db, obj.project_id)
    await db.commit()
    await db.refresh(obj)
    return ProjectStageInstanceOut.model_validate(obj)

