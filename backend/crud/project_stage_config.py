from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.project_stage_config import ProjectStageConfig


async def list_project_stage_configs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[UUID] = None
) -> List[ProjectStageConfig]:
    """List project stage configs with optional filters"""
    query = select(ProjectStageConfig)
    
    if project_id:
        query = query.where(ProjectStageConfig.project_id == project_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_project_stage_config(
    db: AsyncSession, config_id: UUID
) -> Optional[ProjectStageConfig]:
    """Get single project stage config by ID"""
    query = select(ProjectStageConfig).where(ProjectStageConfig.id == config_id)
    result = await db.execute(query)
    return result.scalars().first()