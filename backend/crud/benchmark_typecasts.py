from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.benchmark_mastertypes import BenchmarkMastertype
from models.benchmark_typecasts import BenchmarkTypecast
from models.background_grade_metrics import BackgroundGradeMetric
from models.jurisdictions import Jurisdiction


def _typecast_row_to_dict(row) -> Dict[str, Any]:
    tc: BenchmarkTypecast = row[0]
    return {
        "id": tc.id,
        "code": tc.code,
        "name": tc.name,
        "mastertype_id": tc.mastertype_id,
        "mastertype_name": row.mastertype_name,
    }


async def list_benchmark_typecasts(
    db: AsyncSession,
    mastertype_id: Optional[UUID] = None,
    jurisdiction_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = (
        select(BenchmarkTypecast, BenchmarkMastertype.name.label("mastertype_name"))
        .outerjoin(BenchmarkMastertype, BenchmarkMastertype.id == BenchmarkTypecast.mastertype_id)
        .order_by(BenchmarkMastertype.name, BenchmarkTypecast.name)
    )
    if mastertype_id is not None:
        q = q.where(BenchmarkTypecast.mastertype_id == mastertype_id)
    
    if jurisdiction_name:
        jur_result = await db.execute(
            select(Jurisdiction.id).where(Jurisdiction.name == jurisdiction_name)
        )
        jurisdiction_id = jur_result.scalar_one_or_none()
        
        if jurisdiction_id:
            tc_ids_query = (
                select(distinct(BackgroundGradeMetric.typecast_id))
                .where(BackgroundGradeMetric.jurisdiction_id == jurisdiction_id)
                .where(BackgroundGradeMetric.typecast_id.isnot(None))
            )
            
            tc_ids_result = await db.execute(tc_ids_query)
            valid_typecast_ids = tc_ids_result.scalars().all()
            
            if valid_typecast_ids:
                q = q.where(BenchmarkTypecast.id.in_(valid_typecast_ids))
            else:
                 # No typecasts found for this jurisdiction, return empty results
                return []
    
    result = await db.execute(q)
    return [_typecast_row_to_dict(row) for row in result.all()]


async def get_benchmark_typecast(db: AsyncSession, typecast_id: UUID) -> Optional[Dict[str, Any]]:
    q = (
        select(BenchmarkTypecast, BenchmarkMastertype.name.label("mastertype_name"))
        .outerjoin(BenchmarkMastertype, BenchmarkMastertype.id == BenchmarkTypecast.mastertype_id)
        .where(BenchmarkTypecast.id == typecast_id)
    )
    result = await db.execute(q)
    row = result.first()
    return _typecast_row_to_dict(row) if row else None
