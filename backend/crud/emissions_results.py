from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.emissions_results import EmissionsResult


async def upsert_result(
    db: AsyncSession,
    *,
    project_id: UUID,
    project_stage_instance_id: UUID,
    activity_data_id: UUID,
    value_key: str,
    lifecycle_module_code: Optional[str] = None,
    is_supplementary: bool = False,
    value: Decimal,
    unit_id: Optional[UUID] = None,
) -> EmissionsResult:
    stmt = (
        pg_insert(EmissionsResult)
        .values(
            project_id=project_id,
            project_stage_instance_id=project_stage_instance_id,
            activity_data_id=activity_data_id,
            value_key=value_key,
            lifecycle_module_code=lifecycle_module_code,
            is_supplementary=is_supplementary,
            value=value,
            unit_id=unit_id,
        )
        .on_conflict_do_update(
            constraint="emissions_results_activity_value_key",
            set_={"value": value, "unit_id": unit_id, "lifecycle_module_code": lifecycle_module_code},
        )
        .returning(EmissionsResult)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.scalars().first()


async def list_results_for_stage(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> List[EmissionsResult]:
    q = select(EmissionsResult).where(
        EmissionsResult.project_stage_instance_id == stage_instance_id
    )
    result = await db.execute(q)
    return result.scalars().all()


async def list_results_for_activity(
    db: AsyncSession,
    activity_data_id: UUID,
) -> List[EmissionsResult]:
    q = select(EmissionsResult).where(EmissionsResult.activity_data_id == activity_data_id)
    result = await db.execute(q)
    return result.scalars().all()
