from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import case as sa_case, delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.maintenance_replacement_factors import MaintenanceReplacementFactor
from models.dataset_revisions import DatasetRevision
from models.jurisdictions import Jurisdiction
from models.units import Unit


def _build_row(r) -> dict:
    unit_id = r["unit_id"]
    unit_dict = (
        {"id": unit_id, "code": r["unit_code"], "label": r["unit_label"]}
        if unit_id is not None
        else None
    )
    return {
        "id": r["id"],
        "dataset_revision_id": r["dataset_revision_id"],
        "jurisdiction_id": r["jurisdiction_id"],
        "jurisdiction_name": r["jurisdiction_name"],
        "activity_type": r["activity_type"],
        "item": r["item"],
        "unit_id": unit_id,
        "unit": unit_dict,
        "emissions_intensity_tco2e": r["emissions_intensity_tco2e"],
        "default_frequency_years": r["default_frequency_years"],
        "source_note": r["source_note"],
    }


def _base_query():
    mrf = MaintenanceReplacementFactor.__table__
    j = Jurisdiction.__table__
    u = Unit.__table__
    return (
        select(
            mrf.c.id,
            mrf.c.dataset_revision_id,
            mrf.c.jurisdiction_id,
            j.c.name.label("jurisdiction_name"),
            mrf.c.activity_type,
            mrf.c.item,
            mrf.c.unit_id,
            u.c.code.label("unit_code"),
            u.c.label.label("unit_label"),
            mrf.c.emissions_intensity_tco2e,
            mrf.c.default_frequency_years,
            mrf.c.source_note,
        )
        .outerjoin(j, j.c.id == mrf.c.jurisdiction_id)
        .outerjoin(u, u.c.id == mrf.c.unit_id)
        .order_by(j.c.name, mrf.c.activity_type, mrf.c.item)
    )


async def list_maintenance_replacement_factors(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 500,
) -> List[dict]:
    mrf = MaintenanceReplacementFactor.__table__
    q = _base_query()
    if dataset_revision_id is not None:
        q = q.where(mrf.c.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(mrf.c.jurisdiction_id == jurisdiction_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return [_build_row(r) for r in result.mappings().all()]


async def list_maintenance_replacement_factors_active(
    db: AsyncSession,
    jurisdiction_name: Optional[str] = None,
) -> List[dict]:
    dr = DatasetRevision.__table__
    j = Jurisdiction.__table__

    rev_q = (
        select(dr.c.id)
        .where(dr.c.scope_type == "DEFAULT")
        .order_by(
            sa_case((dr.c.status == "published", 0), else_=1),
            dr.c.id.desc(),
        )
        .limit(1)
    )
    rev_res = await db.execute(rev_q)
    revision_id = rev_res.scalar_one_or_none()
    if revision_id is None:
        return []

    mrf = MaintenanceReplacementFactor.__table__
    q = _base_query().where(mrf.c.dataset_revision_id == revision_id)
    if jurisdiction_name is not None:
        q = q.where(j.c.name == jurisdiction_name)

    result = await db.execute(q)
    return [_build_row(r) for r in result.mappings().all()]


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_maintenance_replacement_factor(
    db: AsyncSession,
    factor_id: UUID,
    emissions_intensity_tco2e: Optional[Decimal],
    default_frequency_years: Optional[int],
    source_note: Optional[str],
) -> Optional[dict]:
    mrf = MaintenanceReplacementFactor.__table__
    res = await db.execute(
        select(mrf.c.dataset_revision_id).where(mrf.c.id == factor_id)
    )
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(mrf).where(mrf.c.id == factor_id).values(
            emissions_intensity_tco2e=emissions_intensity_tco2e,
            default_frequency_years=default_frequency_years,
            source_note=source_note,
        )
    )
    await db.commit()
    rows = await list_maintenance_replacement_factors(db, dataset_revision_id=row[0])
    for r in rows:
        if str(r["id"]) == str(factor_id):
            return r
    return None


async def delete_maintenance_replacement_factor(db: AsyncSession, factor_id: UUID) -> bool:
    mrf = MaintenanceReplacementFactor.__table__
    res = await db.execute(select(mrf.c.dataset_revision_id).where(mrf.c.id == factor_id))
    row = res.first()
    if row is None:
        return False
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be deleted.")
    await db.execute(sa_delete(mrf).where(mrf.c.id == factor_id))
    return True
