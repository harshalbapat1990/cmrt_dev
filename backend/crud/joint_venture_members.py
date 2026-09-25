from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.joint_venture_members import JointVentureMember


async def list_joint_venture_members(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    joint_venture_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> List[JointVentureMember]:
    """List joint venture members with optional filters"""
    query = select(JointVentureMember)
    
    if joint_venture_id:
        query = query.where(JointVentureMember.joint_venture_id == joint_venture_id)
    
    if organization_id:
        query = query.where(JointVentureMember.organization_id == organization_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_joint_venture_member(
    db: AsyncSession, member_id: UUID
) -> Optional[JointVentureMember]:
    """Get single joint venture member by ID"""
    query = select(JointVentureMember).where(JointVentureMember.id == member_id)
    result = await db.execute(query)
    return result.scalars().first()