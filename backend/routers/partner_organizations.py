from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, require_role
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.partner_organizations import (
    list_partner_organizations,
    list_partner_suggestions,
    review_partner_suggestion,
    submit_partner_suggestion,
)
from schemas.partner_organizations import (
    PartnerOrganizationOut,
    PartnerOrganizationSuggestionCreate,
    PartnerOrganizationSuggestionOut,
    PartnerOrganizationSuggestionReview,
)


router = APIRouter(prefix="/api/partner-organizations", tags=["partner-organizations"])


@router.get("", response_model=list[PartnerOrganizationOut])
async def get_partner_organizations(
    partner_type: Literal["DESIGNERS", "CONTRACTORS"],
    q: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=100, ge=1, le=500),
    _principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    return await list_partner_organizations(db, partner_type, q=q, limit=limit)


@router.post("/suggestions", response_model=PartnerOrganizationSuggestionOut)
async def create_partner_suggestion(
    payload: PartnerOrganizationSuggestionCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    suggestion, created = await submit_partner_suggestion(db, payload, principal.user_id)
    if created:
        await write_audit_event(
            db,
            entity_type="partner_organization_suggestion",
            entity_id=suggestion.id,
            action="CREATE",
            performed_by=principal.user_id,
            performed_by_org=principal.organization_id,
            metadata={"name": suggestion.name, "partner_type": suggestion.partner_type},
        )
        await db.commit()
    return suggestion


@router.get("/suggestions/pending", response_model=list[PartnerOrganizationSuggestionOut])
async def get_pending_partner_suggestions(
    _super_admin: None = Depends(require_role(SUPER_ADMIN)),
    _principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    return await list_partner_suggestions(db)


@router.post("/suggestions/{suggestion_id}/review", response_model=PartnerOrganizationSuggestionOut)
async def review_partner_suggestion_endpoint(
    suggestion_id: UUID,
    payload: PartnerOrganizationSuggestionReview,
    principal: Principal = Depends(get_current_principal),
    _super_admin: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    suggestion, partner = await review_partner_suggestion(
        db, suggestion_id, principal.user_id, payload.decision
    )
    await write_audit_event(
        db,
        entity_type="partner_organization_suggestion",
        entity_id=suggestion.id,
        action=payload.decision.upper(),
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={
            "name": suggestion.name,
            "partner_type": suggestion.partner_type,
            "partner_organization_id": str(partner.id) if partner else None,
        },
    )
    await db.commit()
    return suggestion
