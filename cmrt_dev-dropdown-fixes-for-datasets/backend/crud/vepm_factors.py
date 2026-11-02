from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.vepm_factors import VepmFactor
from models.dataset_revisions import DatasetRevision


async def list_vepm_factors(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 5000,
) -> List[dict]:
    vf = VepmFactor.__table__

    q = select(
        vf.c.id,
        vf.c.dataset_revision_id,
        vf.c.year,
        vf.c.speed_kmh,
        vf.c.fleet_average_co2e_g_km,
        vf.c.light_vehicle_co2e_g_km,
        vf.c.heavy_vehicle_co2e_g_km,
        vf.c.bus_co2e_g_km,
    ).order_by(vf.c.year, vf.c.speed_kmh)

    if dataset_revision_id is not None:
        q = q.where(vf.c.dataset_revision_id == dataset_revision_id)
    if year is not None:
        q = q.where(vf.c.year == year)

    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_vepm_factor(
    db: AsyncSession,
    factor_id: UUID,
    fleet_average_co2e_g_km: Optional[float],
    light_vehicle_co2e_g_km: Optional[float],
    heavy_vehicle_co2e_g_km: Optional[float],
    bus_co2e_g_km: Optional[float],
) -> Optional[dict]:
    vf = VepmFactor.__table__
    res = await db.execute(select(vf.c.dataset_revision_id).where(vf.c.id == factor_id))
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(vf).where(vf.c.id == factor_id).values(
            fleet_average_co2e_g_km=fleet_average_co2e_g_km,
            light_vehicle_co2e_g_km=light_vehicle_co2e_g_km,
            heavy_vehicle_co2e_g_km=heavy_vehicle_co2e_g_km,
            bus_co2e_g_km=bus_co2e_g_km,
        )
    )
    await db.commit()
    rows = await list_vepm_factors(db, dataset_revision_id=row[0], skip=0, limit=10000)
    for r in rows:
        if str(r["id"]) == str(factor_id):
            return r
    return None


async def delete_vepm_factor(db: AsyncSession, factor_id: UUID) -> bool:
    vf = VepmFactor.__table__
    res = await db.execute(select(vf.c.dataset_revision_id).where(vf.c.id == factor_id))
    row = res.first()
    if row is None:
        return False
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be deleted.")
    await db.execute(sa_delete(vf).where(vf.c.id == factor_id))
    return True
