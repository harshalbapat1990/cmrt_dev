from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.benchmark_mastertypes import BenchmarkMastertype
from models.background_grade_metrics import BackgroundGradeMetric
from models.jurisdictions import Jurisdiction


async def list_benchmark_mastertypes(
    db: AsyncSession,
    jurisdiction_name: Optional[str] = None,
) -> List[BenchmarkMastertype]:
    if jurisdiction_name:
        jur_result = await db.execute(
            select(Jurisdiction.id).where(Jurisdiction.name == jurisdiction_name)
        )
        jurisdiction_id = jur_result.scalar_one_or_none()
        if jurisdiction_id:
            mt_ids_result = await db.execute(
                select(distinct(BackgroundGradeMetric.mastertype_id))
                .where(BackgroundGradeMetric.jurisdiction_id == jurisdiction_id)
                .where(BackgroundGradeMetric.mastertype_id.isnot(None))
            )
            valid_ids = mt_ids_result.scalars().all()
            result = await db.execute(
                select(BenchmarkMastertype)
                .where(BenchmarkMastertype.id.in_(valid_ids))
                .order_by(BenchmarkMastertype.name)
            )
            return list(result.scalars().all())

    result = await db.execute(select(BenchmarkMastertype).order_by(BenchmarkMastertype.name))
    return list(result.scalars().all())


async def get_benchmark_mastertype(db: AsyncSession, mastertype_id: UUID) -> Optional[BenchmarkMastertype]:
    result = await db.execute(
        select(BenchmarkMastertype).where(BenchmarkMastertype.id == mastertype_id)
    )
    return result.scalars().first()
