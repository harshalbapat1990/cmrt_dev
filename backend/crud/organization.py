from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from models.organizations import Organization
from schemas.organization import OrganizationCreate, OrganizationUpdate


def _coerce_org_type(value):
    if value is None:
        return None
    # Accept either schema Enum, ORM Enum, or raw string.
    try:
        from models.organizations import Organization_Type

        if isinstance(value, Organization_Type):
            return value
        raw = getattr(value, "value", value)
        return Organization_Type(raw)
    except Exception:
        return value

async def create_organization(db: AsyncSession, payload: OrganizationCreate) -> Organization:
    # unique name
    existing = (await db.execute(
        select(Organization).where(Organization.name.ilike(payload.name.strip()))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")
    obj = Organization(
        name=payload.name.strip(), 
        organization_type=_coerce_org_type(payload.organization_type),
        is_active=payload.is_active,
        jurisdiction_id=payload.jurisdiction_id,
        region_id=payload.region_id
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj

async def get_organization(db: AsyncSession, organization_id: UUID) -> Optional[Organization]:
    res = await db.execute(select(Organization).where(Organization.id == organization_id))
    return res.scalar_one_or_none()


async def list_organizations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    organization_type: Optional[str] = None,
    q: Optional[str] = None
) -> List[Organization]:
    query = select(Organization)
    if is_active is not None:
        query = query.where(Organization.is_active == is_active)
    if organization_type:
        query = query.where(Organization.organization_type == _coerce_org_type(organization_type))
    if q:
        from sqlalchemy import func
        query = query.where(func.lower(Organization.name).like(f"%{q.lower()}%"))
    query = query.order_by(Organization.name).offset(skip).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return rows

async def update_organization(db: AsyncSession, obj: Organization, payload: OrganizationUpdate) -> Organization:
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        # check uniqueness
        exists = (await db.execute(
            select(Organization).where(Organization.name.ilike(data["name"].strip()))
        )).scalar_one_or_none()
        if exists and exists.id != obj.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")
        obj.name = data["name"].strip()
    if "organization_type" in data and data["organization_type"]:
        obj.organization_type = _coerce_org_type(data["organization_type"])
    if "is_active" in data and data["is_active"] is not None:
        obj.is_active = data["is_active"]
    if "jurisdiction_id" in data:
        obj.jurisdiction_id = data["jurisdiction_id"]
    if "region_id" in data:
        obj.region_id = data["region_id"]
    await db.flush()
    await db.refresh(obj)
    return obj

async def delete_organization(db: AsyncSession, organization_id: UUID) -> bool:
    obj = await get_organization(db, organization_id)
    if not obj:
        return False
    await db.delete(obj)
    return True