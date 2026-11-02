from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.rbac import get_effective_role_names, SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR
from schemas.project_reporting_submission import (
    ProjectReportingSubmissionOut,
    ProjectReportingSubmissionCreate,
    ProjectReportingSubmissionUpdate,
    ConstructionPeriodCreate,
)
from crud.project_reporting_submission import (
    create_submission, get_submission, list_submissions, update_submission, delete_submission,
    get_or_create_submission,
)
from crud.project import touch_project

router = APIRouter(prefix="/api/project-submissions", tags=["project-submissions"])

_EDITOR_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_EDITOR}
_ADMIN_ROLES = {SUPER_ADMIN, ORG_ADMIN}


async def _require_roles(db: AsyncSession, principal: Principal, project_id: UUID, allowed: set) -> None:
    roles = await get_effective_role_names(db, principal.user_id, project_id)
    if not roles.intersection(allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.post("", response_model=ProjectReportingSubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_new_submission(payload: ProjectReportingSubmissionCreate, db: AsyncSession = Depends(get_session)):
    obj = await create_submission(db, payload)
    await touch_project(db, payload.project_id)
    await db.commit()
    return obj


@router.post("/get-or-create", response_model=ProjectReportingSubmissionOut)
async def get_or_create_submission_period(
    payload: ConstructionPeriodCreate,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_or_create_submission(
        db,
        project_id=payload.project_id,
        stage_instance_id=payload.stage_instance_id,
        period_label=payload.period_label,
        frequency=payload.frequency,
        period_start_date=payload.period_start_date,
        period_end_date=payload.period_end_date,
    )
    await touch_project(db, payload.project_id)
    await db.commit()
    return obj


@router.get("", response_model=List[ProjectReportingSubmissionOut])
async def get_submissions(
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    is_open: Optional[bool] = None,
    db: AsyncSession = Depends(get_session),
):
    objs = await list_submissions(db, skip, limit, project_id, is_open)
    return objs


@router.get("/{submission_id:uuid}", response_model=ProjectReportingSubmissionOut)
async def get_submission_by_id(submission_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_submission(db, submission_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return obj


@router.patch("/{submission_id:uuid}", response_model=ProjectReportingSubmissionOut)
async def patch_submission(
    submission_id: UUID,
    payload: ProjectReportingSubmissionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_submission(db, submission_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    await _require_roles(db, principal, obj.project_id, _EDITOR_ROLES)
    obj = await update_submission(db, obj, payload)
    await touch_project(db, obj.project_id)
    await db.commit()
    return obj


@router.delete("/{submission_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_submission(db, submission_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    await _require_roles(db, principal, obj.project_id, _ADMIN_ROLES)
    ok = await delete_submission(db, submission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    await db.commit()
    return None
