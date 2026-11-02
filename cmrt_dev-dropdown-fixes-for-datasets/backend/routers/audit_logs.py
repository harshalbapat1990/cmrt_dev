"""
routers/audit_logs.py
======================
Scenario 10 — Audit & Governance
  10.1 Every dataset action produces an audit log entry (written in other routers).
  10.2 View revision / entity audit trail via this query endpoint.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.rbac import (
    ORG_ADMIN,
    PROJECT_ADMIN,
    SUPER_ADMIN,
    get_effective_role_names,
    get_org_scoped_role_names,
)
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import list_audit_logs
from models.audit_logs import AuditLog
from models.project_options import ProjectOption
from models.project_stage_instances import ProjectStageInstance
from models.stage_approval_events import StageApprovalEvent
from schemas.audit_logs import AuditLogOut, StageResubmissionAuditOut

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


async def _require_auditor(
    db: AsyncSession,
    principal: Principal,
    project_id: Optional[UUID] = None,
) -> None:
    roles = await get_effective_role_names(db, principal.user_id, project_id=project_id)
    # The collection endpoint has no project context, so effective-role lookup
    # only returns global roles. Include the caller's own organisation scope so
    # an ORG_ADMIN assignment is recognized for audit access.
    if principal.organization_id is not None:
        roles = roles | await get_org_scoped_role_names(
            db, principal.user_id, principal.organization_id
        )
    if not roles.intersection({ORG_ADMIN, SUPER_ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an Org Admin or Super Admin to view audit logs.",
        )


@router.get("", response_model=List[AuditLogOut])
async def get_audit_logs(
    entity_type: Optional[str] = Query(
        None,
        description="e.g. dataset_revision, emissions_factor_set, project_dataset_revision, stage_instance",
    ),
    entity_id: Optional[UUID] = Query(None, description="UUID of the specific entity"),
    action: Optional[str] = Query(
        None,
        description="e.g. CREATE, UPDATE, DELETE",
    ),
    performed_by: Optional[UUID] = Query(None, description="Filter by actor user ID"),
    performed_by_org: Optional[UUID] = Query(None, description="Filter by actor organisation ID"),
    from_date: Optional[datetime] = Query(None, description="Include logs at or after this timestamp (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Include logs at or before this timestamp (ISO 8601)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    """
    View chronological audit trail for any entity.
    Restricted to Org Admin and Super Admin roles.
    Results are ordered most-recent first.
    """
    await _require_auditor(db, principal)
    return await list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        performed_by_org=performed_by_org,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )


@router.get("/project/{project_id}", response_model=List[AuditLogOut])
async def get_project_audit_logs(
    project_id: UUID,
    action: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    await _require_auditor(db, principal, project_id=project_id)

    project_id_str = str(project_id)
    q = (
        select(AuditLog)
        .where(
            or_(
                AuditLog.entity_id == project_id,
                AuditLog.event_metadata["project_id"].astext == project_id_str,
            )
        )
        .order_by(AuditLog.performed_at.desc())
    )
    if action:
        q = q.where(AuditLog.action == action)
    if from_date:
        q = q.where(AuditLog.performed_at >= from_date)
    if to_date:
        q = q.where(AuditLog.performed_at <= to_date)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stage/{stage_instance_id}/resubmission", response_model=StageResubmissionAuditOut)
async def get_stage_resubmission_audit(
    stage_instance_id: UUID,
    project_option_id: Optional[UUID] = Query(None, description="Scope audit to a specific project option (report slot)."),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    si_result = await db.execute(
        select(ProjectStageInstance).where(ProjectStageInstance.id == stage_instance_id)
    )
    si = si_result.scalar_one_or_none()
    if si is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")

    roles = await get_effective_role_names(db, principal.user_id, project_id=si.project_id)
    if not roles.intersection({SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a Project Admin, Org Admin, or Super Admin to view the resubmission audit.",
        )

    opt_filter = [
        ProjectOption.stage_instance_id == stage_instance_id,
        ProjectOption.approval_status == "submitted",
    ]
    if project_option_id:
        opt_filter.append(ProjectOption.id == project_option_id)
    submitted_opt_result = await db.execute(
        select(ProjectOption).where(*opt_filter).limit(1)
    )
    submitted_opt = submitted_opt_result.scalar_one_or_none()

    if submitted_opt is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resubmission audit is only available for stages with a submitted report.",
        )

    stage_instance_id_str = str(stage_instance_id)

    reject_result = await db.execute(
        select(StageApprovalEvent)
        .where(
            StageApprovalEvent.stage_instance_id == stage_instance_id,
            StageApprovalEvent.report_number == submitted_opt.report_number,
            StageApprovalEvent.event_type.in_(["REJECT", "REOPEN", "APPROVE_REOPEN"]),
        )
        .order_by(StageApprovalEvent.performed_at.desc())
        .limit(1)
    )
    reject_event = reject_result.scalar_one_or_none()

    if reject_event is None:
        return StageResubmissionAuditOut(
            has_prior_rejection=False,
            window_from=None,
            window_to=None,
            stage_name=si.stage.value if si.stage else "",
            rows=[],
        )

    window_from = reject_event.performed_at

    submit_result = await db.execute(
        select(StageApprovalEvent)
        .where(
            StageApprovalEvent.stage_instance_id == stage_instance_id,
            StageApprovalEvent.report_number == submitted_opt.report_number,
            StageApprovalEvent.event_type == "SUBMIT",
            StageApprovalEvent.performed_at > window_from,
        )
        .order_by(StageApprovalEvent.performed_at.desc())
        .limit(1)
    )
    submit_event = submit_result.scalar_one_or_none()
    window_to = submit_event.performed_at if submit_event else datetime.utcnow()

    opt_id_str = str(submitted_opt.id)
    opt_label = submitted_opt.label
    rows_result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.event_metadata["stage_instance_id"].astext == stage_instance_id_str,
            AuditLog.performed_at >= window_from,
            AuditLog.performed_at <= window_to,
            or_(
                AuditLog.event_metadata["project_option_id"].astext == opt_id_str,
                and_(
                    AuditLog.event_metadata["option_label"].astext == opt_label,
                    AuditLog.event_metadata["report_number"].astext == str(submitted_opt.report_number),
                ),
            ),
        )
        .order_by(AuditLog.performed_at.asc())
    )
    rows = rows_result.scalars().all()

    return StageResubmissionAuditOut(
        has_prior_rejection=True,
        window_from=window_from,
        window_to=window_to,
        stage_name=si.stage.value if si.stage else "",
        rows=rows,
    )
