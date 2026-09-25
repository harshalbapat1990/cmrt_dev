from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.freight_rail_factors import FreightRailFactor
from models.dataset_revisions import DatasetRevision


async def list_freight_rail_factors(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[dict]:
    frf = FreightRailFactor.__table__

    q = select(
        frf.c.id,
        frf.c.dataset_revision_id,
        frf.c.train_type,
        frf.c.terrain,
        frf.c.fuel_consumption_l_per_000_gtk,
        frf.c.source_note,
    ).order_by(frf.c.train_type, frf.c.terrain)

    if dataset_revision_id is not None:
        q = q.where(frf.c.dataset_revision_id == dataset_revision_id)

    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_freight_rail_factor(
    db: AsyncSession,
    factor_id: UUID,
    fuel_consumption_l_per_000_gtk: Optional[float],
    source_note: Optional[str],
) -> Optional[dict]:
    frf = FreightRailFactor.__table__
    res = await db.execute(select(frf.c.dataset_revision_id).where(frf.c.id == factor_id))
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(frf).where(frf.c.id == factor_id).values(
            fuel_consumption_l_per_000_gtk=fuel_consumption_l_per_000_gtk,
            source_note=source_note,
        )
    )
    await db.commit()
    rows = await list_freight_rail_factors(db, dataset_revision_id=row[0], skip=0, limit=500)
    for r in rows:
        if str(r["id"]) == str(factor_id):
            return r
    return None


async def delete_freight_rail_factor(db: AsyncSession, factor_id: UUID) -> bool:
    frf = FreightRailFactor.__table__
    res = await db.execute(select(frf.c.dataset_revision_id).where(frf.c.id == factor_id))
    row = res.first()
    if row is None:
        return False
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be deleted.")
    await db.execute(sa_delete(frf).where(frf.c.id == factor_id))
    return True
