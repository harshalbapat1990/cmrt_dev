"""
crud/organization_domains.py
============================
CRUD for organization allowed email domains.
SUPER_ADMIN only (enforced at router layer).
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.organisation_domains import OrganizationDomain


async def list_domains_for_org(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    active_only: bool = True,
) -> List[OrganizationDomain]:
    query = select(OrganizationDomain).where(
        OrganizationDomain.organization_id == organisation_id
    )
    if active_only:
        query = query.where(OrganizationDomain.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


async def get_domain_by_value(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    domain: str,
) -> Optional[OrganizationDomain]:
    result = await db.execute(
        select(OrganizationDomain).where(
            OrganizationDomain.organization_id == organisation_id,
            OrganizationDomain.domain == domain.lower(),
        )
    )
    return result.scalars().first()


async def add_domain(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    domain: str,
) -> OrganizationDomain:
    """Add (or reactivate) an allowed domain for an organisation."""
    existing = await get_domain_by_value(db, organisation_id, domain)
    if existing:
        if not existing.is_active:
            existing.is_active = True
            await db.flush()
        return existing

    obj = OrganizationDomain(
        organization_id=organisation_id,
        domain=domain.lower(),
        is_active=True,
    )
    db.add(obj)
    await db.flush()
    return obj


async def deactivate_domain(
    db: AsyncSession,
    domain_id: uuid.UUID,
) -> Optional[OrganizationDomain]:
    """Soft-deactivate a domain."""
    result = await db.execute(
        select(OrganizationDomain).where(OrganizationDomain.id == domain_id)
    )
    obj = result.scalars().first()
    if obj:
        obj.is_active = False
        await db.flush()
    return obj


async def domain_matches_org(
    db: AsyncSession,
    organisation_id: uuid.UUID,
    email: str,
) -> bool:
    """
    Return True if the email's domain matches any active allowed domain for
    the given organisation. Domain comparison is case-insensitive.
    """
    domains = await list_domains_for_org(db, organisation_id, active_only=True)
    if not domains:
        return False  # Secure default: no domains = no self-registration

    email_domain = email.lower().split("@")[-1]
    allowed = {d.domain.lower() for d in domains}
    return email_domain in allowed
