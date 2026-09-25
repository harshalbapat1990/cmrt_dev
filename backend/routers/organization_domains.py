"""
routers/organization_domains.py
================================
Allowed email-domain management for organisations.
Access: SUPER_ADMIN only.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, require_role
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.organization_domains import (
    add_domain,
    deactivate_domain,
    list_domains_for_org,
)
from schemas.organisation_domains import OrganizationDomainOut

router = APIRouter(prefix="/api/organizations/{org_id}/domains", tags=["org-domains"])

_sa_only = Depends(require_role(SUPER_ADMIN))


@router.get("", response_model=list[OrganizationDomainOut])
async def list_org_domains(
    org_id: UUID,
    active_only: bool = True,
    _: None = _sa_only,
    db: AsyncSession = Depends(get_session),
):
    """List allowed email domains for an organisation."""
    return await list_domains_for_org(db, org_id, active_only=active_only)


@router.post("", response_model=OrganizationDomainOut, status_code=status.HTTP_201_CREATED)
async def add_org_domain(
    org_id: UUID,
    domain: str,
    principal: Principal = Depends(get_current_principal),
    _: None = _sa_only,
    db: AsyncSession = Depends(get_session),
):
    """Add (or reactivate) an allowed email domain. SUPER_ADMIN only."""
    # Validate org exists
    from sqlalchemy import select
    from models.organizations import Organization

    res = await db.execute(select(Organization).where(Organization.id == org_id))
    if not res.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    obj = await add_domain(db, org_id, domain.lower().strip())
    await write_audit_event(
        db,
        entity_type="organisation_domain",
        entity_id=obj.id,
        action="ADD",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        new_value=domain.lower().strip(),
        metadata={"organisation_id": str(org_id)},
    )
    await db.commit()
    return obj


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_org_domain(
    org_id: UUID,
    domain_id: UUID,
    principal: Principal = Depends(get_current_principal),
    _: None = _sa_only,
    db: AsyncSession = Depends(get_session),
):
    """Soft-deactivate an allowed domain. SUPER_ADMIN only."""
    obj = await deactivate_domain(db, domain_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    await write_audit_event(
        db,
        entity_type="organisation_domain",
        entity_id=domain_id,
        action="DEACTIVATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"organisation_id": str(org_id)},
    )
    await db.commit()
    return None
