
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit_diff import compute_field_diffs, orm_to_audit_dict
from core.authorization_policy import AccessLevel, can_manage_stage_access
from core.rbac import (
    ORG_ADMIN, 
    SUPER_ADMIN, 
    PROJECT_ADMIN, 
    get_org_scoped_role_names,
    get_effective_role_names, 
    require_project_access
)
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from schemas.project import ProjectOut, ProjectCreate, ProjectUpdate, ReportingBoundaryOut
from crud.project import (
    create_project,
    get_project,
    list_projects_for_user_roles,
    update_project,
    delete_project,
    get_reporting_boundaries,
)

from crud.project_reporting_submission import generate_submissions_for_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    payload: ProjectCreate,
    auto_generate_submissions: bool = Query(
        False,
        description="If true, pre-create reporting periods based on stage config or recurring first_submission_month",
    ),
    periods: int = Query(
        12,
        ge=1,
        le=60,
        description="Number of future periods to generate if auto_generate_submissions is true",
    ),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    global_roles = await get_org_scoped_role_names(
        db, principal.user_id, payload.proponent_org_id
    )
    if not global_roles.intersection({ORG_ADMIN, SUPER_ADMIN}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be ORG_ADMIN for this organisation to create a project.",
        )

    obj = await create_project(db, payload)

    if auto_generate_submissions:
        await generate_submissions_for_project(db, obj, periods=periods)

    await write_audit_event(
        db,
        entity_type="project",
        entity_id=obj.id,
        action="CREATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"project_name": obj.project_name, "proponent_org_id": str(payload.proponent_org_id)},
    )
    await db.commit()
    refreshed = await get_project(db, obj.id)
    return refreshed


@router.get("", response_model=List[ProjectOut])
async def get_projects(
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    
    objs = await list_projects_for_user_roles(
        db, 
        principal.user_id, 
        is_active=is_active,
        skip=skip, 
        limit=limit
    )
    return objs


@router.get("/{id:uuid}", response_model=ProjectOut)
async def get_project_by_id(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_project(db, id)
    
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Project not found"
        )

    await require_project_access(
        db,
        principal,
        id,
        AccessLevel.VIEW
    )
    return obj


@router.patch("/{id:uuid}", response_model=ProjectOut)
async def patch_project(
    id: UUID,
    payload: ProjectUpdate,
    auto_generate_submissions: bool = Query(
        False, description="If true, (re)generate future reporting periods after update"
    ),
    periods: int = Query(12, ge=1, le=60),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):

    obj = await get_project(db, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    
    await require_project_access(
        db,
        principal,
        id,
        AccessLevel.ADMIN
    )

    # Stage access is centrally managed by ORG_ADMIN only.
    # PROJECT_ADMIN has ADMIN access to the project/stages themselves,
    # but does not automatically gain permission to manage stage assignments.
    if payload.member_accesses is not None:
        effective_roles = await get_effective_role_names(
            db,
            principal.user_id,
            project_id=id,
        )

        if not can_manage_stage_access(effective_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage project stage access.",
            )

    _TRACKED_PROJECT_FIELDS = [
        "project_name", "project_description", "project_type_id", "project_typecast_id",
        "proponent_org_id", "is_active", "project_capex_million", "project_opex",
        "declared_unit_value", "declared_unit_type", "first_submission_month",
    ]
    before = orm_to_audit_dict(obj, _TRACKED_PROJECT_FIELDS)

    obj = await update_project(db, obj, payload)
    after = orm_to_audit_dict(obj, _TRACKED_PROJECT_FIELDS)
    diffs = compute_field_diffs(before, after)

    if auto_generate_submissions:
        await generate_submissions_for_project(db, obj, periods=periods)

    await write_audit_event(
        db,
        entity_type="project",
        entity_id=id,
        action="UPDATE",
        entity_name=f"Project: {obj.project_name}",
        metadata={"field_diffs": diffs} if diffs else None,
    )
    await db.commit()
    refreshed = await get_project(db, id)
    return refreshed


@router.get("/{id:uuid}/reporting-boundaries", response_model=List[ReportingBoundaryOut])
async def get_project_reporting_boundaries(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    await require_project_access(
        db,
        principal,
        id,
        AccessLevel.VIEW
    )
    rows = await get_reporting_boundaries(db, id)
    return [ReportingBoundaryOut.model_validate(r) for r in rows]


@router.delete("/{id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_project(db, id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    await require_project_access(
        db,
        principal,
        id,
        AccessLevel.ADMIN
    )
    
    project_name = obj.project_name
    ok = await delete_project(db, id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    await write_audit_event(
        db,
        entity_type="project",
        entity_id=id,
        action="DELETE",
        entity_name=f"Project: {project_name}",
    )
    await db.commit()
    return None


async def _require_project_admin(
        db: AsyncSession, 
        principal: Principal, 
        project_id: UUID
) -> None:
    await require_project_access(
        db,
        principal,
        project_id,
        AccessLevel.ADMIN
    )


@router.patch("/{id:uuid}/close", response_model=ProjectOut)
async def close_project(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_project(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await _require_project_admin(db, principal, id)
    obj.is_active = False
    obj.updated_on = datetime.utcnow()
    await db.flush()
    await write_audit_event(
        db,
        entity_type="project",
        entity_id=id,
        action="CLOSE",
        entity_name=f"Project: {obj.project_name}",
    )
    await db.commit()
    return await get_project(db, id)


@router.patch("/{id:uuid}/reopen", response_model=ProjectOut)
async def reopen_project(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_project(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await _require_project_admin(db, principal, id)
    obj.is_active = True
    obj.updated_on = datetime.utcnow()
    await db.flush()
    await write_audit_event(
        db,
        entity_type="project",
        entity_id=id,
        action="REOPEN",
        entity_name=f"Project: {obj.project_name}",
    )
    await db.commit()
    return await get_project(db, id)