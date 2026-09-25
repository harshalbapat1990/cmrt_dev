from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.rbac import require_stage_access
from core.authorization_policy import AccessLevel
# from core.rbac import (
#     get_effective_role_names,
#     SUPER_ADMIN,
#     ORG_ADMIN,
#     PROJECT_ADMIN,
#     PROJECT_EDITOR,
# )
from schemas.project_reporting_submission import ConstructionPeriodCreate, ConstructionPeriodOut
from crud.project_reporting_submission import (
    create_construction_period,
    list_construction_periods,
    get_construction_period,
    set_period_status,
    auto_create_next_period,
    seed_first_period,
    get_emissions_by_period_ids,
    get_total_construction_emissions,
)
from crud.stage_approval_events import record_event

router = APIRouter(prefix="/api/construction-periods", tags=["construction-periods"])

# ADMIN_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN}
# EDITOR_OR_ABOVE = {SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR}
# EDITOR_ONLY = {SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR}


# async def _require_roles(
#     db: AsyncSession,
#     principal: Principal,
#     project_id: UUID,
#     allowed: set[str],
#     detail: str = "Insufficient permissions",
# ) -> None:
#     roles = await get_effective_role_names(db, principal.user_id, project_id)
#     if not roles.intersection(allowed):
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def _get_period_or_404(db: AsyncSession, period_id: UUID):
    obj = await get_construction_period(db, period_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Construction period not found")
    return obj


@router.get("", response_model=List[ConstructionPeriodOut])
async def get_construction_periods(
    stage_instance_id: UUID = Query(..., description="The construction stage instance ID"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    stage_instance = await get_project_stage_instance(
        db,
        stage_instance_id,
    )

    if not stage_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage instance not found",
        )

    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.VIEW,
    )

    periods = await list_construction_periods(
        db,
        stage_instance_id,
    )

    period_ids = [p.id for p in periods]
    emissions_map = await get_emissions_by_period_ids(
        db,
        period_ids,
    )

    all_periods_total = await get_total_construction_emissions(
        db,
        stage_instance_id,
    )

    result = []

    for idx, period in enumerate(periods):
        period_out = ConstructionPeriodOut.model_validate(period)

        period_out.period_emissions_tco2e = emissions_map.get(period.id)

        period_out.previous_period_emissions_tco2e = (
            emissions_map.get(periods[idx - 1].id)
            if idx > 0
            else None
        )

        period_out.all_periods_emissions_tco2e = all_periods_total

        result.append(period_out)

    return result

@router.post("", response_model=ConstructionPeriodOut, status_code=status.HTTP_201_CREATED)
async def create_period(
    payload: ConstructionPeriodCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    await require_stage_access(
        db,
        principal,
        payload.project_id,
        payload.stage_instance_id,
        AccessLevel.EDIT,
    )
    obj = await create_construction_period(db, payload)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{period_id}/submit", response_model=ConstructionPeriodOut)
async def submit_period(
    period_id: UUID,
    comment: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status not in ("in_progress", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit a period with status '{period.status}'",
        )

    from_status = period.status
    period = await set_period_status(
        db, period, "awaiting_approval",
        submitted_by=principal.user_id,
        submitted_at=datetime.utcnow(),
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="submitted",
        performed_by=principal.user_id,
        from_status=from_status,
        to_status="awaiting_approval",
        justification=comment,
        submission_period_id=period.id,
    )
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/approve", response_model=ConstructionPeriodOut)
async def approve_period(
    period_id: UUID,
    comment: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve a period with status '{period.status}'",
        )

    period = await set_period_status(
        db, period, "approved",
        decision_by=principal.user_id,
        decision_at=datetime.utcnow(),
        rejection_reason=None,
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="approved",
        performed_by=principal.user_id,
        from_status="awaiting_approval",
        to_status="approved",
        justification=comment,
        submission_period_id=period.id,
    )

    try:
        await auto_create_next_period(db, period)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("auto_create_next_period failed: %s", exc)

    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/reject", response_model=ConstructionPeriodOut)
async def reject_period(
    period_id: UUID,
    rejection_reason: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject a period with status '{period.status}'",
        )

    period = await set_period_status(
        db, period, "rejected",
        decision_by=principal.user_id,
        decision_at=datetime.utcnow(),
        rejection_reason=rejection_reason,
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="rejected",
        performed_by=principal.user_id,
        from_status="awaiting_approval",
        to_status="rejected",
        justification=rejection_reason,
        submission_period_id=period.id,
    )
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/request-reopen", response_model=ConstructionPeriodOut)
async def request_reopen_period(
    period_id: UUID,
    reopen_reason: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot request reopen for a period with status '{period.status}'",
        )

    period = await set_period_status(
        db, period, "reopen_requested",
        reopen_requested_by=principal.user_id,
        reopen_requested_at=datetime.utcnow(),
        reopen_reason=reopen_reason,
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="reopen_requested",
        performed_by=principal.user_id,
        from_status="approved",
        to_status="reopen_requested",
        justification=reopen_reason,
        submission_period_id=period.id,
    )
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/approve-reopen", response_model=ConstructionPeriodOut)
async def approve_reopen_period(
    period_id: UUID,
    comment: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status != "reopen_requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve reopen for a period with status '{period.status}'",
        )

    period = await set_period_status(
        db, period, "in_progress",
        decision_by=principal.user_id,
        decision_at=datetime.utcnow(),
        rejection_reason=None,
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="reopen_approved",
        performed_by=principal.user_id,
        from_status="reopen_requested",
        to_status="in_progress",
        justification=comment,
        submission_period_id=period.id,
    )
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{period_id}/reject-reopen", response_model=ConstructionPeriodOut)
async def reject_reopen_period(
    period_id: UUID,
    rejection_reason: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )

    if period.status != "reopen_requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject reopen for a period with status '{period.status}'",
        )

    period = await set_period_status(
        db, period, "approved",
        decision_by=principal.user_id,
        decision_at=datetime.utcnow(),
        rejection_reason=rejection_reason,
    )
    await record_event(
        db,
        stage_instance_id=period.stage_instance_id,
        project_id=period.project_id,
        event_type="reopen_rejected",
        performed_by=principal.user_id,
        from_status="reopen_requested",
        to_status="approved",
        justification=rejection_reason,
        submission_period_id=period.id,
    )
    await db.commit()
    await db.refresh(period)
    return period


@router.patch("/{period_id}/exec-summary", response_model=ConstructionPeriodOut)
async def save_period_exec_summary(
    period_id: UUID,
    exec_summary: Optional[str] = Body(None, embed=True),
    exec_summary_author: Optional[str] = Body(None, embed=True),
    exec_summary_date: Optional[datetime] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    period = await _get_period_or_404(db, period_id)
    await require_stage_access(
        db,
        principal,
        period.project_id,
        period.stage_instance_id,
        AccessLevel.EDIT,
    )
    period.exec_summary = exec_summary
    period.exec_summary_author = exec_summary_author if exec_summary else None
    period.exec_summary_date = exec_summary_date.replace(tzinfo=None) if exec_summary and exec_summary_date else None
    period.updated_on = datetime.utcnow()
    db.add(period)
    await db.flush()
    await db.refresh(period)
    await db.commit()
    return period
