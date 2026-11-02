from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.grade_definitions import GradeDefinition
from schemas.grade_definitions import GradeDefinitionCreate, GradeDefinitionUpdate


async def create_grade_definition(db: AsyncSession, payload: GradeDefinitionCreate) -> GradeDefinition:
    obj = GradeDefinition(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_grade_definition(db: AsyncSession, grade_id: int) -> Optional[GradeDefinition]:
    result = await db.execute(select(GradeDefinition).where(GradeDefinition.id == grade_id))
    return result.scalars().first()


async def list_grade_definitions(db: AsyncSession) -> List[GradeDefinition]:
    result = await db.execute(select(GradeDefinition).order_by(GradeDefinition.id))
    return result.scalars().all()


async def update_grade_definition(
    db: AsyncSession, obj: GradeDefinition, payload: GradeDefinitionUpdate
) -> GradeDefinition:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_grade_definition(db: AsyncSession, grade_id: int) -> bool:
    obj = await get_grade_definition(db, grade_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
