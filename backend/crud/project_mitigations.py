from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project_mitigations import ProjectMitigation


async def list_project_mitigations(
    db: AsyncSession,
    stage_instance_id: UUID,
    project_option_id: Optional[UUID] = None,
    submission_stage: Optional[str] = None,
) -> List[ProjectMitigation]:
    q = select(ProjectMitigation).where(ProjectMitigation.project_stage_instance_id == stage_instance_id)
    if project_option_id is not None:
        q = q.where(ProjectMitigation.project_option_id == project_option_id)
    if submission_stage is not None:
        q = q.where(ProjectMitigation.submission_stage == submission_stage)
    q = q.order_by(ProjectMitigation.created_at)
    result = await db.execute(q)
    return result.scalars().all()


async def get_project_mitigation(db: AsyncSession, mitigation_id: UUID) -> Optional[ProjectMitigation]:
    result = await db.execute(select(ProjectMitigation).where(ProjectMitigation.id == mitigation_id))
    return result.scalars().first()


async def create_project_mitigation(db: AsyncSession, payload: dict) -> ProjectMitigation:
    obj = ProjectMitigation(**payload)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_project_mitigation(
    db: AsyncSession,
    mitigation_id: UUID,
    patch: dict,
) -> Optional[ProjectMitigation]:
    obj = await get_project_mitigation(db, mitigation_id)
    if not obj:
        return None
    for k, v in patch.items():
        setattr(obj, k, v)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project_mitigation(db: AsyncSession, mitigation_id: UUID) -> bool:
    obj = await get_project_mitigation(db, mitigation_id)
    if not obj:
        return False
    await db.delete(obj)
    await db.flush()
    return True