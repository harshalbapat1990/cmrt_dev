from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.joint_ventures import JointVenture


async def list_joint_ventures(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> List[JointVenture]:
    """List all joint ventures"""
    query = select(JointVenture).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_joint_venture(db: AsyncSession, joint_venture_id: UUID) -> Optional[JointVenture]:
    """Get single joint venture by ID"""
    query = select(JointVenture).where(JointVenture.id == joint_venture_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_joint_venture_by_name(db: AsyncSession, name: str) -> Optional[JointVenture]:
    """Get joint venture by name"""
    query = select(JointVenture).where(JointVenture.name == name)
    result = await db.execute(query)
    return result.scalars().first()