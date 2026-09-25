from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.rbac import (
    require_stage_access,
)
from core.authorization_policy import AccessLevel
# from core.rbac import get_effective_role_names, SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR
from crud.activity_data import copy_option_data
from models.project_options import ProjectOption
from crud.project_options import (
    list_project_options,
    get_or_create_options_for_stage,
    get_project_option,
    create_sub_option,
    rename_project_option,
    set_default_project_option,
    delete_project_option,
    set_report_options_status,
    get_total_emissions_for_option,
)
from crud.project_stage_instances import get_project_stage_instance
from crud.project import touch_project
from crud.stage_approval_events import record_event
from schemas.project_options import ProjectOptionOut

router = APIRouter(prefix="/api/project-options", tags=["project-options"])

# _SUBMIT_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR}


@router.get("", response_model=List[ProjectOptionOut])
async def get_options_for_stage(
    stage_instance_id: UUID = Query(..., description="Stage instance ID"),
    report_number: Optional[int] = Query(None, description="Filter by report number"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    stage_instance = await get_project_stage_instance(db, stage_instance_id)
    if not stage_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Stage instance not found."
        )
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance_id,
        AccessLevel.VIEW
    )
    options = await list_project_options(
        db, 
        stage_instance.project_id, 
        stage_instance_id, 
        report_number
    )
    return options


@router.post("/ensure", response_model=List[ProjectOptionOut], status_code=status.HTTP_200_OK)
async def ensure_options_for_stage(
    stage_instance_id: UUID = Query(..., description="Stage instance ID"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    stage_instance = await get_project_stage_instance(db, stage_instance_id)
    if not stage_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Stage instance not found."
        )

    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance_id,
        AccessLevel.EDIT
    )
    options = await get_or_create_options_for_stage(
        db, 
        stage_instance
    )
    await touch_project(
        db, 
        stage_instance.project_id
    )
    await db.commit()

    results = []
    for opt in options:
        out = ProjectOptionOut.model_validate(opt)
        out.total_emissions_tco2e = await get_total_emissions_for_option(db, opt.id)
        results.append(out)
    return results


from pydantic import BaseModel


class CreateSubOptionBody(BaseModel):
    project_id: UUID
    stage_instance_id: UUID
    report_number: int
    label: str


class RenameOptionBody(BaseModel):
    label: str


@router.post("", response_model=ProjectOptionOut, status_code=status.HTTP_201_CREATED)
async def add_sub_option(
    body: CreateSubOptionBody,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await create_sub_option(
        db,
        project_id=body.project_id,
        stage_instance_id=body.stage_instance_id,
        report_number=body.report_number,
        label=body.label,
    )
    await require_stage_access(
        db,
        principal,
        body.project_id,
        body.stage_instance_id,
        AccessLevel.EDIT
    )
    await touch_project(db, body.project_id)
    await db.commit()
    await db.refresh(opt)
    return opt


@router.patch("/{option_id}/rename", response_model=ProjectOptionOut)
async def rename_option(
    option_id: UUID,
    body: RenameOptionBody,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await rename_project_option(db, option_id, body.label)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.EDIT
    )
    if not opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found.")
    await touch_project(db, opt.project_id)
    await db.commit()
    await db.refresh(opt)
    return opt


@router.post("/{option_id}/set-default", response_model=ProjectOptionOut)
async def set_default_option(
    option_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await set_default_project_option(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.EDIT
    )
    if not opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found.")
    await touch_project(db, opt.project_id)
    await db.commit()
    await db.refresh(opt)
    return opt


@router.delete("/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_option(
    option_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await get_project_option(db, option_id)
    project_id = opt.project_id if opt else None
    await require_stage_access(
        db,
        principal,
        project_id,
        None,
        AccessLevel.EDIT
    )
    await delete_project_option(db, option_id)
    if project_id:
        await touch_project(db, project_id)
    await db.commit()


@router.post("/{source_id}/copy-to/{target_id}", status_code=status.HTTP_200_OK)
async def copy_option_data_endpoint(
    source_id: UUID,
    target_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    source = await get_project_option(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source option not found.")
    target = await get_project_option(db, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target option not found.")
    await require_stage_access(
        db,
        principal,
        source.project_id,
        source.stage_instance_id,
        AccessLevel.EDIT
    )
    await require_stage_access(
        db,
        principal,
        target.project_id,
        target.stage_instance_id,
        AccessLevel.EDIT
    )

    if source.stage_instance_id != target.stage_instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target options must belong to the same stage instance.",
        )
    if source.report_number != target.report_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target options must belong to the same report.",
        )
    if source_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target options must be different.",
        )

    count = await copy_option_data(db, source_id, target_id)
    await touch_project(db, source.project_id)
    await db.commit()
    return {"copied": count}


async def _get_option_or_404(db: AsyncSession, option_id: UUID) -> "ProjectOption":
    opt = await get_project_option(db, option_id)
    if not opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found.")
    return opt


@router.post("/{option_id}/submit", response_model=List[ProjectOptionOut])
async def submit_report(
    option_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    stage_instance = await get_project_stage_instance(db, opt.stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.EDIT
    )
    if opt.approval_status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report must be 'draft' or 'rejected' to submit (currently '{opt.approval_status}')",
        )
    from_status = opt.approval_status
    updated = await set_report_options_status(db, opt.stage_instance_id, opt.report_number, "submitted")
    await record_event(
        db,
        stage_instance_id=opt.stage_instance_id,
        project_id=stage_instance.project_id,
        event_type="SUBMIT",
        performed_by=principal.user_id,
        from_status=from_status,
        to_status="submitted",
        report_number=opt.report_number,
    )
    await touch_project(db, stage_instance.project_id)
    await db.commit()
    return updated


@router.post("/{option_id}/approve", response_model=List[ProjectOptionOut])
async def approve_report(
    option_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.ADMIN
    )
    if opt.approval_status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report must be 'submitted' to approve (currently '{opt.approval_status}')",
        )
    updated = await set_report_options_status(db, opt.stage_instance_id, opt.report_number, "final_approved")
    await touch_project(db, opt.project_id)
    await db.commit()
    return updated


@router.post("/{option_id}/reject", response_model=List[ProjectOptionOut])
async def reject_report(
    option_id: UUID,
    justification: str = Body(..., embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.ADMIN
    )
    if not justification or not justification.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Justification is required when rejecting a report",
        )
    if opt.approval_status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report must be 'submitted' to reject (currently '{opt.approval_status}')",
        )
    updated = await set_report_options_status(
        db, opt.stage_instance_id, opt.report_number, "rejected", justification=justification.strip()
    )
    stage_instance = await get_project_stage_instance(db, opt.stage_instance_id)
    if stage_instance:
        await record_event(
            db,
            stage_instance_id=opt.stage_instance_id,
            project_id=stage_instance.project_id,
            event_type="REJECT",
            performed_by=principal.user_id,
            from_status="submitted",
            to_status="rejected",
            justification=justification.strip(),
            report_number=opt.report_number,
        )
    await touch_project(db, opt.project_id)
    await db.commit()
    return updated


@router.post("/{option_id}/request-reopen", response_model=List[ProjectOptionOut])
async def request_report_reopen(
    option_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.ADMIN
    )
    if opt.approval_status not in ("final_approved", "submitted"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot request reopen from status '{opt.approval_status}'",
        )
    updated = await set_report_options_status(
        db, opt.stage_instance_id, opt.report_number, "pending_reopen", justification=justification
    )
    await touch_project(db, opt.project_id)
    await db.commit()
    return updated


@router.post("/{option_id}/approve-reopen", response_model=List[ProjectOptionOut])
async def approve_report_reopen(
    option_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.ADMIN
    )
    if opt.approval_status != "pending_reopen":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report must be 'pending_reopen' (currently '{opt.approval_status}')",
        )
    updated = await set_report_options_status(db, opt.stage_instance_id, opt.report_number, "draft")
    await touch_project(db, opt.project_id)
    await db.commit()
    return updated


@router.post("/{option_id}/reject-reopen", response_model=List[ProjectOptionOut])
async def reject_report_reopen(
    option_id: UUID,
    justification: Optional[str] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.ADMIN
    )
    if opt.approval_status != "pending_reopen":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report must be 'pending_reopen' (currently '{opt.approval_status}')",
        )
    updated = await set_report_options_status(
        db, opt.stage_instance_id, opt.report_number, "final_approved"
    )
    await touch_project(db, opt.project_id)
    await db.commit()
    return updated


@router.patch("/{option_id}/exec-summary", response_model=ProjectOptionOut)
async def save_option_exec_summary(
    option_id: UUID,
    exec_summary: Optional[str] = Body(None, embed=True),
    exec_summary_author: Optional[str] = Body(None, embed=True),
    exec_summary_date: Optional[datetime] = Body(None, embed=True),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    opt = await _get_option_or_404(db, option_id)
    await require_stage_access(
        db,
        principal,
        opt.project_id,
        opt.stage_instance_id,
        AccessLevel.EDIT
    )
    opt.exec_summary = exec_summary
    opt.exec_summary_author = exec_summary_author if exec_summary else None
    opt.exec_summary_date = exec_summary_date.replace(tzinfo=None) if exec_summary and exec_summary_date else None
    db.add(opt)
    await db.flush()
    await db.refresh(opt)
    await touch_project(db, opt.project_id)
    await db.commit()
    return opt

