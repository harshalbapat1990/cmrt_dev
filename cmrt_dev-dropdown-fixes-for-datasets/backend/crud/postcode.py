from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import UUID
from models.postcode import PostcodeReference
from typing import List, Optional
from uuid import UUID as UUIDType

async def get_all_postcode_references(db: AsyncSession) -> List[PostcodeReference]:
    result = await db.execute(
        select(PostcodeReference).options(selectinload(PostcodeReference.jurisdiction))
    )
    return result.scalars().all()

async def get_postcode_reference_by_postcode(
    db: AsyncSession, postcode: str, jurisdiction_id: UUIDType
) -> Optional[PostcodeReference]:
    result = await db.execute(
        select(PostcodeReference)
        .where(
            (PostcodeReference.postcode == postcode) 
            & (PostcodeReference.jurisdiction_id == jurisdiction_id)
        )
        .options(selectinload(PostcodeReference.jurisdiction))
    )
    return result.scalars().first()

async def get_postcode_references_by_jurisdiction(
    db: AsyncSession, jurisdiction_id: UUIDType
) -> List[PostcodeReference]:
    """Get all postcodes for a specific jurisdiction"""
    result = await db.execute(
        select(PostcodeReference)
        .where(PostcodeReference.jurisdiction_id == jurisdiction_id)
        .options(selectinload(PostcodeReference.jurisdiction))
    )
    return result.scalars().all()

async def upsert_postcode_reference(
    db: AsyncSession, 
    postcode: str, 
    jurisdiction_id: UUIDType, 
    area_class
) -> tuple[PostcodeReference, bool]:
    """Upsert a postcode reference. Returns (record, is_created)"""
    existing = await get_postcode_reference_by_postcode(db, postcode, jurisdiction_id)
    
    if existing:
        if existing.area_class != area_class:
            existing.area_class = area_class
        return existing, False
    else:
        new_record = PostcodeReference(
            postcode=postcode,
            jurisdiction_id=jurisdiction_id,
            area_class=area_class
        )
        db.add(new_record)
        return new_record, True
