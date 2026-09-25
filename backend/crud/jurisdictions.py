from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.jurisdictions import Jurisdiction
from schemas.jurisdictions import JurisdictionCreate, JurisdictionUpdate


async def create_jurisdiction(db: AsyncSession, payload: JurisdictionCreate) -> Jurisdiction:
    obj = Jurisdiction(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_jurisdiction(db: AsyncSession, jurisdiction_id: UUID) -> Optional[Jurisdiction]:
    result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == jurisdiction_id))
    return result.scalars().first()


async def get_jurisdiction_by_name(db: AsyncSession, name: str, type: Optional[str] = None) -> Optional[Jurisdiction]:
    query = select(Jurisdiction).where(Jurisdiction.name == name)
    if type:
        query = query.where(Jurisdiction.type == type)
    result = await db.execute(query)
    return result.scalars().first()


async def list_jurisdictions(db: AsyncSession, skip: int = 0, limit: int = 100, type: Optional[str] = None, parent_id: Optional[UUID] = None) -> List[Jurisdiction]:
    query = select(Jurisdiction)
    if type:
        query = query.where(Jurisdiction.type == type)
    if parent_id:
        query = query.where(Jurisdiction.parent_id == parent_id)
    query = query.order_by(Jurisdiction.name).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_regions_by_country(db: AsyncSession, country_name: str) -> List[Jurisdiction]:
    """Get all regions for a specific country"""
    # First get the country jurisdiction
    country_result = await db.execute(
        select(Jurisdiction).where(
            (Jurisdiction.name == country_name) & (Jurisdiction.type == "country")
        )
    )
    country = country_result.scalars().first()
    if not country:
        return []
    
    # Then get all regions with this country as parent
    regions_result = await db.execute(
        select(Jurisdiction).where(
            (Jurisdiction.parent_id == country.id) & (Jurisdiction.type == "region")
        ).order_by(Jurisdiction.name)
    )
    return regions_result.scalars().all()


async def update_jurisdiction(db: AsyncSession, obj: Jurisdiction, payload: JurisdictionUpdate) -> Jurisdiction:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_jurisdiction(db: AsyncSession, jurisdiction_id: UUID) -> bool:
    obj = await get_jurisdiction(db, jurisdiction_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
