from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.background_grade_metrics import BackgroundGradeMetric
from models.emissions_factor_sets import EmissionsFactorSet
from schemas.emissions_factor_sets import EmissionsFactorSetCreate, EmissionsFactorSetUpdate


async def create_emissions_factor_set(db: AsyncSession, payload: EmissionsFactorSetCreate) -> EmissionsFactorSet:
    obj = EmissionsFactorSet(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_emissions_factor_set(db: AsyncSession, factor_set_id: UUID) -> Optional[EmissionsFactorSet]:
    result = await db.execute(select(EmissionsFactorSet).where(EmissionsFactorSet.id == factor_set_id))
    return result.scalars().first()


async def count_factor_sets_for_revision(db: AsyncSession, revision_id: UUID) -> int:
    """Count factor rows attached to a revision in the current delta schema.

    Older revisions stored these rows under emissions_factor_sets, but the
    active migration lineage removed that table and stores revision ownership
    directly on background_grade_metrics. Keep the function name for existing
    callers while querying the live schema.
    """
    result = await db.execute(
        select(func.count(BackgroundGradeMetric.id)).where(
            BackgroundGradeMetric.dataset_revision_id == revision_id
        )
    )
    return int(result.scalar() or 0)


async def update_emissions_factor_set(
    db: AsyncSession, obj: EmissionsFactorSet, payload: EmissionsFactorSetUpdate
) -> EmissionsFactorSet:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_emissions_factor_set(db: AsyncSession, factor_set_id: UUID) -> bool:
    obj = await get_emissions_factor_set(db, factor_set_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
