from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.project_parties import ProjectParty


async def list_project_parties(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    joint_venture_id: Optional[UUID] = None
) -> List[ProjectParty]:
    """List project parties with optional filters"""
    query = select(ProjectParty)
    
    if project_id:
        query = query.where(ProjectParty.project_id == project_id)
    
    if organization_id:
        query = query.where(ProjectParty.organization_id == organization_id)
    
    if joint_venture_id:
        query = query.where(ProjectParty.joint_venture_id == joint_venture_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_project_party(
    db: AsyncSession, party_id: UUID
) -> Optional[ProjectParty]:
    """Get single project party by ID"""
    query = select(ProjectParty).where(ProjectParty.id == party_id)
    result = await db.execute(query)
    return result.scalars().first()