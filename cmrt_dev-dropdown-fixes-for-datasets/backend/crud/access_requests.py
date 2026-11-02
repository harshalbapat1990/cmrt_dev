from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.access_requests import AccessRequest
from schemas.access_requests import AccessRequestCreate


async def create_access_request(
    db: AsyncSession,
    payload: AccessRequestCreate,
    requester_user_id: uuid.UUID,
) -> AccessRequest:
    obj = AccessRequest(
        request_type=payload.request_type,
        status="PENDING",
        requester_user_id=requester_user_id,
        target_user_id=payload.target_user_id,
        requested_role_id=payload.requested_role_id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        organisation_id=payload.organisation_id,
        project_id=payload.project_id,
        reason=payload.reason,
        event_metadata=payload.metadata,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_access_request(
    db: AsyncSession,
    request_id: uuid.UUID,
) -> Optional[AccessRequest]:
    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    return result.scalars().first()


async def list_access_requests(
    db: AsyncSession,
    *,
    status_filter: Optional[str] = None,
    request_type: Optional[str] = None,
    organisation_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    project_ids: Optional[List[uuid.UUID]] = None,
    target_user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[AccessRequest]:
    query = select(AccessRequest)
    if status_filter:
        query = query.where(AccessRequest.status == status_filter.upper())
    if request_type:
        query = query.where(AccessRequest.request_type == request_type.upper())
    if organisation_id:
        query = query.where(AccessRequest.organisation_id == organisation_id)
    if project_id:
        query = query.where(AccessRequest.project_id == project_id)
    if project_ids is not None:
        query = query.where(AccessRequest.project_id.in_(project_ids))
    if target_user_id:
        query = query.where(AccessRequest.target_user_id == target_user_id)
    query = query.order_by(AccessRequest.created_on.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def list_access_requests_enriched(
    db: AsyncSession,
    *,
    status_filter: Optional[str] = None,
    request_type: Optional[str] = None,
    organisation_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    project_ids: Optional[List[uuid.UUID]] = None,
    target_user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    from models.users import User
    from models.organizations import Organization
    from models.project import Project

    RequesterUser = aliased(User, name="req_user")

    display_name = func.nullif(
        func.trim(
            func.coalesce(RequesterUser.first_name, "")
            + " "
            + func.coalesce(RequesterUser.last_name, "")
        ),
        "",
    ).label("requester_display_name")

    query = (
        select(
            AccessRequest,
            RequesterUser.email.label("requester_email"),
            display_name,
            Organization.name.label("organisation_name"),
            Project.project_name.label("project_name"),
            Project.project_class.label("project_class"),
        )
        .outerjoin(RequesterUser, RequesterUser.id == AccessRequest.requester_user_id)
        .outerjoin(Organization, Organization.id == AccessRequest.organisation_id)
        .outerjoin(Project, Project.id == AccessRequest.project_id)
    )

    if status_filter:
        query = query.where(AccessRequest.status == status_filter.upper())
    if request_type:
        query = query.where(AccessRequest.request_type == request_type.upper())
    if organisation_id:
        query = query.where(
            or_(
                AccessRequest.organisation_id == organisation_id,
                Project.proponent_org_id == organisation_id,
            )
        )
    if project_id:
        query = query.where(AccessRequest.project_id == project_id)
    if project_ids is not None:
        query = query.where(AccessRequest.project_id.in_(project_ids))
    if target_user_id:
        query = query.where(AccessRequest.target_user_id == target_user_id)

    query = query.order_by(AccessRequest.created_on.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    enriched: List[Dict[str, Any]] = []
    for row in rows:
        ar: AccessRequest = row[0]
        enriched.append(
            {
                "id": ar.id,
                "request_type": ar.request_type,
                "status": ar.status,
                "requester_user_id": ar.requester_user_id,
                "target_user_id": ar.target_user_id,
                "requested_role_id": ar.requested_role_id,
                "scope_type": ar.scope_type,
                "scope_id": ar.scope_id,
                "organisation_id": ar.organisation_id,
                "project_id": ar.project_id,
                "reason": ar.reason,
                "decision_note": ar.decision_note,
                "reviewed_by_user_id": ar.reviewed_by_user_id,
                "reviewed_at": ar.reviewed_at,
                "created_on": ar.created_on,
                "updated_on": ar.updated_on,
                "requester_email": row.requester_email,
                "requester_display_name": row.requester_display_name,
                "organisation_name": row.organisation_name,
                "project_name": row.project_name,
                "project_class": row.project_class.value if row.project_class is not None else None,
            }
        )
    return enriched


async def _transition(
    db: AsyncSession,
    request_id: uuid.UUID,
    new_status: str,
    reviewer_user_id: uuid.UUID,
    decision_note: Optional[str],
) -> AccessRequest:
    obj = await get_access_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    if obj.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {obj.status}",
        )
    obj.status = new_status
    obj.reviewed_by_user_id = reviewer_user_id
    obj.reviewed_at = datetime.utcnow()
    obj.decision_note = decision_note
    obj.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(obj)
    return obj


async def approve_access_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    reviewer_user_id: uuid.UUID,
    decision_note: Optional[str] = None,
) -> AccessRequest:
    return await _transition(db, request_id, "APPROVED", reviewer_user_id, decision_note)


async def reject_access_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    reviewer_user_id: uuid.UUID,
    decision_note: Optional[str] = None,
) -> AccessRequest:
    return await _transition(db, request_id, "REJECTED", reviewer_user_id, decision_note)


async def cancel_access_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    requester_user_id: uuid.UUID,
) -> AccessRequest:
    obj = await get_access_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")
    if obj.requester_user_id != requester_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester can cancel")
    if obj.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {obj.status}",
        )
    obj.status = "CANCELLED"
    obj.updated_on = datetime.utcnow()
    await db.flush()
    await db.refresh(obj)
    return obj
