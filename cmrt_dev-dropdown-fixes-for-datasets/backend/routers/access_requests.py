from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import (
    GLOBAL,
    ORGANISATION,
    SUPER_ADMIN,
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    assert_can_grant_role,
    get_effective_role_names,
    get_org_scoped_role_names,
    get_project_ids_where_admin,
)
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.access_requests import (
    approve_access_request,
    cancel_access_request,
    create_access_request,
    get_access_request,
    list_access_requests,
    list_access_requests_enriched,
    reject_access_request,
)
from crud.user_roles import create_user_role
from models.roles import Role
from models.project import Project as ProjectModel
from models.user_roles import UserRole
from models.access_requests import AccessRequest
from schemas.access_requests import AccessRequestCreate, AccessRequestDecision, AccessRequestOut, AccessRequestEnrichedOut

router = APIRouter(prefix="/api/access-requests", tags=["access-requests"])


@router.post("", response_model=AccessRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: AccessRequestCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    if payload.request_type.upper() == SUPER_ADMIN:
        if payload.target_user_id not in (None, principal.user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only request Super Admin access for yourself")
        if payload.scope_type.upper() != GLOBAL or payload.scope_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Super Admin requests must use GLOBAL scope with no scope ID")
        if not payload.reason or not payload.reason.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A reason is required for a Super Admin request")
        payload.request_type = SUPER_ADMIN
        payload.target_user_id = principal.user_id
        payload.scope_type = GLOBAL
        payload.scope_id = None
        payload.organisation_id = None
        payload.project_id = None

        super_admin_role = await db.execute(select(Role).where(Role.name == SUPER_ADMIN))
        role = super_admin_role.scalars().first()
        if role is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SUPER_ADMIN role is not configured")
        active_role = await db.execute(select(UserRole.id).where(
            UserRole.user_id == principal.user_id,
            UserRole.role_id == role.id,
            UserRole.scope_type == GLOBAL,
            UserRole.scope_id.is_(None),
            UserRole.is_active == True,
        ).limit(1))
        if active_role.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have Super Admin access")
        pending = await db.execute(select(AccessRequest.id).where(
            AccessRequest.requester_user_id == principal.user_id,
            AccessRequest.target_user_id == principal.user_id,
            AccessRequest.request_type == SUPER_ADMIN,
            AccessRequest.scope_type == GLOBAL,
            AccessRequest.scope_id.is_(None),
            AccessRequest.status == "PENDING",
        ).limit(1))
        if pending.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a pending Super Admin request")
        payload.requested_role_id = role.id

    if payload.target_user_id is None:
        payload.target_user_id = principal.user_id
    obj = await create_access_request(db, payload, requester_user_id=principal.user_id)

    if obj.requested_role_id is None and obj.request_type in (
        "PROJECT_ADMIN", "PROJECT_EDITOR", "PROJECT_VIEWER", "ORG_ADMIN", "SUPER_ADMIN"
    ):
        role_res = await db.execute(select(Role).where(Role.name == obj.request_type))
        role = role_res.scalars().first()
        if role:
            obj.requested_role_id = role.id
            await db.flush()

    await write_audit_event(
        db,
        entity_type="access_request",
        entity_id=obj.id,
        action="CREATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"request_type": obj.request_type, "scope_type": obj.scope_type},
    )
    await db.commit()
    return obj


@router.get("/mine/super-admin", response_model=Optional[AccessRequestOut])
async def get_my_super_admin_request(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(AccessRequest)
        .where(
            AccessRequest.requester_user_id == principal.user_id,
            AccessRequest.target_user_id == principal.user_id,
            AccessRequest.request_type == SUPER_ADMIN,
            AccessRequest.scope_type == GLOBAL,
            AccessRequest.scope_id.is_(None),
        )
        .order_by(AccessRequest.created_on.desc())
        .limit(1)
    )
    return result.scalars().first()


@router.get("", response_model=List[AccessRequestEnrichedOut])
async def list_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    request_type: Optional[str] = None,
    organisation_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    target_user_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = Query(50, ge=1, le=500),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    
    if principal.organization_id is not None:
        effective_roles = await get_org_scoped_role_names(
            db, principal.user_id, principal.organization_id
        )
    else:
        effective_roles = await get_effective_role_names(db, principal.user_id)

    admin_project_ids: Optional[list[UUID]] = None
    if SUPER_ADMIN not in effective_roles:
        if ORG_ADMIN in effective_roles:
            if organisation_id is None:
                organisation_id = principal.organization_id
        else:
            admin_project_ids = await get_project_ids_where_admin(db, principal.user_id)
            if not admin_project_ids:
                target_user_id = principal.user_id

    return await list_access_requests_enriched(
        db,
        status_filter=status_filter,
        request_type=request_type,
        organisation_id=organisation_id,
        project_id=project_id,
        project_ids=admin_project_ids,
        target_user_id=target_user_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=AccessRequestOut)
async def get_request(
    request_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_access_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    effective_roles = await get_effective_role_names(
        db, principal.user_id, project_id=obj.project_id
    )
    is_acting_admin = (
        (ORG_ADMIN in effective_roles and obj.organisation_id is not None)
        or (PROJECT_ADMIN in effective_roles and obj.project_id is not None)
    )
    if (
        SUPER_ADMIN not in effective_roles
        and principal.user_id not in (obj.requester_user_id, obj.target_user_id)
        and not is_acting_admin
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return obj


@router.post("/{request_id}/approve", response_model=AccessRequestOut)
async def approve_request(
    request_id: UUID,
    body: AccessRequestDecision = AccessRequestDecision(),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_access_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    effective_roles = await get_effective_role_names(
        db, principal.user_id, project_id=obj.project_id
    )

    if obj.request_type == "SUPER_ADMIN":
        if SUPER_ADMIN not in effective_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can approve platform operator access requests",
            )
        if (
            obj.requester_user_id != obj.target_user_id
            or obj.scope_type != GLOBAL
            or obj.scope_id is not None
        ):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Super Admin request scope or target")

    elif obj.request_type == "ORG_ADMIN":
        if SUPER_ADMIN not in effective_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can approve Org Admin requests",
            )

    elif obj.request_type == "PROJECT_ADMIN":
        org_roles = await get_org_scoped_role_names(
            db, principal.user_id, obj.organisation_id
        )
        if ORG_ADMIN not in org_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ORG_ADMIN can approve Project Admin requests",
            )

    elif obj.request_type in ("PROJECT_EDITOR", "PROJECT_VIEWER"):
        if obj.organisation_id:
            org_id = obj.organisation_id
        elif obj.project_id:
            proj = await db.get(ProjectModel, obj.project_id)
            org_id = proj.proponent_org_id if proj else None
        else:
            org_id = None
        org_roles = await get_org_scoped_role_names(db, principal.user_id, org_id) if org_id else set()
        if PROJECT_ADMIN not in effective_roles and ORG_ADMIN not in org_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only PROJECT_ADMIN or ORG_ADMIN can approve project access requests",
            )

    obj = await approve_access_request(
        db, request_id, principal.user_id, body.decision_note
    )

    if obj.requested_role_id and obj.target_user_id:
        role_query = select(Role).where(
            Role.name == SUPER_ADMIN if obj.request_type == SUPER_ADMIN else Role.id == obj.requested_role_id
        )
        role_res = await db.execute(role_query)
        role = role_res.scalars().first()
        if role:
            await assert_can_grant_role(
                db, principal, role.name, obj.scope_type, obj.scope_id
            )
            existing_res = await db.execute(
                select(UserRole).where(
                    and_(
                        UserRole.user_id == obj.target_user_id,
                        UserRole.role_id == obj.requested_role_id,
                        UserRole.scope_type == obj.scope_type,
                        UserRole.scope_id == obj.scope_id,
                    )
                )
            )
            existing_ur = existing_res.scalars().first()
            if existing_ur:
                if not existing_ur.is_active:
                    existing_ur.is_active = True
                    await db.flush()
                    await write_audit_event(
                        db, entity_type="user_role", entity_id=existing_ur.id,
                        action="REACTIVATE_SUPER_ADMIN" if role.name == SUPER_ADMIN else "REACTIVATE",
                        performed_by=principal.user_id,
                        performed_by_org=principal.organization_id,
                        metadata={"target_user_id": str(obj.target_user_id), "role": role.name, "scope_type": obj.scope_type},
                    )
            else:
                granted_role = await create_user_role(
                    db,
                    user_id=obj.target_user_id,
                    role_id=role.id,
                    scope_type=obj.scope_type,
                    scope_id=obj.scope_id,
                    is_active=True,
                )
                await write_audit_event(
                    db, entity_type="user_role", entity_id=granted_role.id,
                    action="GRANT_SUPER_ADMIN" if role.name == SUPER_ADMIN else "GRANT",
                    performed_by=principal.user_id,
                    performed_by_org=principal.organization_id,
                    metadata={"target_user_id": str(obj.target_user_id), "role": role.name, "scope_type": obj.scope_type},
                )

    await write_audit_event(
        db,
        entity_type="access_request",
        entity_id=obj.id,
        action="APPROVE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "decision_note": body.decision_note,
            "target_user_id": str(obj.target_user_id),
            "request_type": obj.request_type,
        },
    )
    await db.commit()
    return obj


@router.post("/{request_id}/reject", response_model=AccessRequestOut)
async def reject_request(
    request_id: UUID,
    body: AccessRequestDecision = AccessRequestDecision(),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_access_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    effective_roles = await get_effective_role_names(
        db, principal.user_id, project_id=obj.project_id
    )
    if obj.request_type == "SUPER_ADMIN":
        if SUPER_ADMIN not in effective_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can reject platform operator access requests",
            )
    elif obj.request_type == "ORG_ADMIN":
        if SUPER_ADMIN not in effective_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can reject Org Admin requests",
            )
    elif obj.request_type == "PROJECT_ADMIN":
        org_roles = await get_org_scoped_role_names(
            db, principal.user_id, obj.organisation_id
        )
        if ORG_ADMIN not in org_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ORG_ADMIN can reject Project Admin requests",
            )
    elif obj.request_type in ("PROJECT_EDITOR", "PROJECT_VIEWER"):
        org_roles = (
            await get_org_scoped_role_names(db, principal.user_id, obj.organisation_id)
            if obj.organisation_id
            else set()
        )
        if PROJECT_ADMIN not in effective_roles and ORG_ADMIN not in org_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only PROJECT_ADMIN or ORG_ADMIN can reject project access requests",
            )

    obj = await reject_access_request(db, request_id, principal.user_id, body.decision_note)
    await write_audit_event(
        db,
        entity_type="access_request",
        entity_id=obj.id,
        action="REJECT",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"decision_note": body.decision_note, "request_type": obj.request_type},
    )
    await db.commit()
    return obj


@router.post("/{request_id}/cancel", response_model=AccessRequestOut)
async def cancel_request(
    request_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await cancel_access_request(db, request_id, requester_user_id=principal.user_id)
    await write_audit_event(
        db,
        entity_type="access_request",
        entity_id=obj.id,
        action="CANCEL",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
    )
    await db.commit()
    return obj
