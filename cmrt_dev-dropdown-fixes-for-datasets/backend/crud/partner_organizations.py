from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.partner_organizations import PartnerOrganization, PartnerOrganizationSuggestion
from schemas.partner_organizations import (
    PartnerOrganizationSuggestionCreate,
    normalize_partner_name,
)


async def list_partner_organizations(
    db: AsyncSession,
    partner_type: str,
    q: str | None = None,
    limit: int = 100,
) -> list[PartnerOrganization]:
    query = select(PartnerOrganization).where(
        PartnerOrganization.partner_type == partner_type,
        PartnerOrganization.is_active.is_(True),
    )
    if q and q.strip():
        query = query.where(PartnerOrganization.name.ilike(f"%{q.strip()}%"))
    result = await db.execute(query.order_by(PartnerOrganization.name).limit(limit))
    return list(result.scalars().all())


async def submit_partner_suggestion(
    db: AsyncSession,
    payload: PartnerOrganizationSuggestionCreate,
    submitted_by_user_id: UUID,
) -> tuple[PartnerOrganizationSuggestion, bool]:
    name = " ".join(payload.name.split())
    normalized_name = normalize_partner_name(name)
    partner_type = payload.partner_type

    existing_partner = await db.execute(select(PartnerOrganization).where(
        PartnerOrganization.partner_type == partner_type,
        PartnerOrganization.normalized_name == normalized_name,
    ))
    if existing_partner.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "partner_already_exists", "message": "This partner is already in the directory."},
        )

    existing_result = await db.execute(select(PartnerOrganizationSuggestion).where(
        PartnerOrganizationSuggestion.partner_type == partner_type,
        PartnerOrganizationSuggestion.normalized_name == normalized_name,
        PartnerOrganizationSuggestion.status == "pending",
    ))
    existing = existing_result.scalars().first()
    if existing:
        return existing, False

    rejected_result = await db.execute(select(PartnerOrganizationSuggestion).where(
        PartnerOrganizationSuggestion.partner_type == partner_type,
        PartnerOrganizationSuggestion.normalized_name == normalized_name,
        PartnerOrganizationSuggestion.status == "rejected",
    ).order_by(PartnerOrganizationSuggestion.created_at.desc()))
    rejected = rejected_result.scalars().first()
    if rejected:
        rejected.name = name
        rejected.status = "pending"
        rejected.submitted_by_user_id = submitted_by_user_id
        rejected.reviewed_by_user_id = None
        rejected.reviewed_at = None
        await db.flush()
        return rejected, True

    suggestion = PartnerOrganizationSuggestion(
        name=name,
        normalized_name=normalized_name,
        partner_type=partner_type,
        submitted_by_user_id=submitted_by_user_id,
    )
    try:
        async with db.begin_nested():
            db.add(suggestion)
            await db.flush()
    except IntegrityError:
        result = await db.execute(select(PartnerOrganizationSuggestion).where(
            PartnerOrganizationSuggestion.partner_type == partner_type,
            PartnerOrganizationSuggestion.normalized_name == normalized_name,
            PartnerOrganizationSuggestion.status == "pending",
        ))
        concurrent = result.scalars().first()
        if concurrent:
            return concurrent, False
        raise
    return suggestion, True


async def list_partner_suggestions(db: AsyncSession) -> list[PartnerOrganizationSuggestion]:
    result = await db.execute(select(PartnerOrganizationSuggestion).where(
        PartnerOrganizationSuggestion.status == "pending"
    ).order_by(PartnerOrganizationSuggestion.created_at, PartnerOrganizationSuggestion.id))
    return list(result.scalars().all())


async def review_partner_suggestion(
    db: AsyncSession,
    suggestion_id: UUID,
    reviewer_user_id: UUID,
    decision: str,
) -> tuple[PartnerOrganizationSuggestion, PartnerOrganization | None]:
    result = await db.execute(select(PartnerOrganizationSuggestion).where(
        PartnerOrganizationSuggestion.id == suggestion_id
    ))
    suggestion = result.scalars().first()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Partner suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=409, detail="This partner suggestion has already been reviewed")

    partner = None
    if decision == "approved":
        existing = await db.execute(select(PartnerOrganization).where(
            PartnerOrganization.partner_type == suggestion.partner_type,
            PartnerOrganization.normalized_name == suggestion.normalized_name,
        ))
        partner = existing.scalars().first()
        if partner is None:
            partner = PartnerOrganization(
                name=suggestion.name,
                normalized_name=suggestion.normalized_name,
                partner_type=suggestion.partner_type,
                created_by_user_id=reviewer_user_id,
            )
            try:
                async with db.begin_nested():
                    db.add(partner)
                    await db.flush()
            except IntegrityError:
                existing = await db.execute(select(PartnerOrganization).where(
                    PartnerOrganization.partner_type == suggestion.partner_type,
                    PartnerOrganization.normalized_name == suggestion.normalized_name,
                ))
                partner = existing.scalars().first()
                if partner is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Another administrator added this partner at the same time. Refresh the directory and review again.",
                    )
        suggestion.partner_organization_id = partner.id

    suggestion.status = decision
    suggestion.reviewed_by_user_id = reviewer_user_id
    suggestion.reviewed_at = datetime.utcnow()
    db.add(suggestion)
    await db.flush()
    return suggestion, partner
