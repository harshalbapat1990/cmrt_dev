from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ev_uptake_factors import EvUptakeFactor
from models.ev_scenario_types import EvScenarioType
from models.ev_vehicle_categories import EvVehicleCategory
from models.ev_energy_types import EvEnergyType
from models.jurisdictions import Jurisdiction
from models.dataset_revisions import DatasetRevision


async def list_ev_uptake_factors(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    scenario_code: Optional[str] = None,
    vehicle_category_code: Optional[str] = None,
    energy_type_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 5000,
) -> List[dict]:
    jur = Jurisdiction.__table__.alias("jur")
    sc = EvScenarioType.__table__.alias("sc")
    vc = EvVehicleCategory.__table__.alias("vc")
    et = EvEnergyType.__table__.alias("et")
    ev = EvUptakeFactor.__table__

    q = (
        select(
            ev.c.id,
            ev.c.dataset_revision_id,
            ev.c.jurisdiction_id,
            jur.c.name.label("jurisdiction_name"),
            ev.c.scenario_code,
            sc.c.name.label("scenario_name"),
            ev.c.vehicle_category_code,
            vc.c.name.label("vehicle_category_name"),
            ev.c.energy_type_code,
            et.c.name.label("energy_type_name"),
            ev.c.year,
            ev.c.uptake_pct,
        )
        .select_from(
            ev
            .join(jur, ev.c.jurisdiction_id == jur.c.id)
            .join(sc, ev.c.scenario_code == sc.c.code)
            .join(vc, ev.c.vehicle_category_code == vc.c.code)
            .join(et, ev.c.energy_type_code == et.c.code)
        )
        .order_by(sc.c.name, jur.c.name, vc.c.name, et.c.name, ev.c.year)
    )

    if dataset_revision_id is not None:
        q = q.where(ev.c.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(ev.c.jurisdiction_id == jurisdiction_id)
    if scenario_code is not None:
        q = q.where(ev.c.scenario_code == scenario_code)
    if vehicle_category_code is not None:
        q = q.where(ev.c.vehicle_category_code == vehicle_category_code)
    if energy_type_code is not None:
        q = q.where(ev.c.energy_type_code == energy_type_code)

    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_ev_uptake_factor(
    db: AsyncSession,
    factor_id: UUID,
    uptake_pct: Optional[float],
) -> Optional[dict]:
    ev = EvUptakeFactor.__table__
    res = await db.execute(select(ev.c.dataset_revision_id).where(ev.c.id == factor_id))
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(ev).where(ev.c.id == factor_id).values(uptake_pct=uptake_pct)
    )
    await db.commit()
    rows = await list_ev_uptake_factors(db, dataset_revision_id=row[0], skip=0, limit=100000)
    for r in rows:
        if str(r["id"]) == str(factor_id):
            return r
    return None


async def create_ev_uptake_series(
    db: AsyncSession,
    dataset_revision_id: UUID,
    jurisdiction_id: UUID,
    scenario_code: str,
    vehicle_category_code: str,
    energy_type_code: str,
    year_from: int,
    year_to: int,
) -> List[dict]:
    status = await _get_revision_status(db, dataset_revision_id)
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    ev = EvUptakeFactor.__table__
    existing_res = await db.execute(
        select(ev.c.year).where(
            ev.c.dataset_revision_id == dataset_revision_id,
            ev.c.jurisdiction_id == jurisdiction_id,
            ev.c.scenario_code == scenario_code,
            ev.c.vehicle_category_code == vehicle_category_code,
            ev.c.energy_type_code == energy_type_code,
        )
    )
    existing_years = {r[0] for r in existing_res.fetchall()}
    for year in range(year_from, year_to + 1):
        if year not in existing_years:
            await db.execute(
                ev.insert().values(
                    dataset_revision_id=dataset_revision_id,
                    jurisdiction_id=jurisdiction_id,
                    scenario_code=scenario_code,
                    vehicle_category_code=vehicle_category_code,
                    energy_type_code=energy_type_code,
                    year=year,
                    uptake_pct=None,
                )
            )
    await db.commit()
    return await list_ev_uptake_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        scenario_code=scenario_code,
        vehicle_category_code=vehicle_category_code,
        energy_type_code=energy_type_code,
        skip=0,
        limit=10000,
    )
