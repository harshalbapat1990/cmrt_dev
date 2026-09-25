from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.electric_decarb_factors import ElectricDecarbFactor
from models.decarb_factor_types import DecarbFactorType
from models.jurisdictions import Jurisdiction
from models.grid_regions import GridRegion
from models.dataset_revisions import DatasetRevision
from models.units import Unit


async def list_electric_decarb_factors(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    factor_type_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 5000,
) -> List[dict]:
    jur_alias = Jurisdiction.__table__.alias("jur")
    region_alias = GridRegion.__table__.alias("rgn")
    ft_alias = DecarbFactorType.__table__.alias("ft")
    u_alias = Unit.__table__.alias("u")
    edf = ElectricDecarbFactor.__table__

    q = (
        select(
            edf.c.id,
            edf.c.dataset_revision_id,
            edf.c.factor_type_code,
            ft_alias.c.name.label("factor_type_name"),
            edf.c.jurisdiction_id,
            jur_alias.c.name.label("jurisdiction_name"),
            edf.c.region_id,
            region_alias.c.name.label("region_name"),
            edf.c.unit_id,
            u_alias.c.code.label("unit_code"),
            u_alias.c.label.label("unit_label"),
            edf.c.year,
            edf.c.value,
            edf.c.value_qualifier,
        )
        .select_from(
            edf
            .join(ft_alias, edf.c.factor_type_code == ft_alias.c.code)
            .join(jur_alias, edf.c.jurisdiction_id == jur_alias.c.id)
            .outerjoin(region_alias, edf.c.region_id == region_alias.c.id)
            .outerjoin(u_alias, edf.c.unit_id == u_alias.c.id)
        )
        .order_by(edf.c.factor_type_code, jur_alias.c.name, region_alias.c.name, edf.c.year)
    )

    if dataset_revision_id is not None:
        q = q.where(edf.c.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(edf.c.jurisdiction_id == jurisdiction_id)
    if factor_type_code is not None:
        q = q.where(edf.c.factor_type_code == factor_type_code)

    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        unit_id = d.pop("unit_id", None)
        unit_code = d.pop("unit_code", None)
        unit_label = d.pop("unit_label", None)
        d["unit_id"] = unit_id
        d["unit"] = {"id": unit_id, "code": unit_code, "label": unit_label} if unit_id else None
        out.append(d)
    return out


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_electric_decarb_factor(
    db: AsyncSession,
    factor_id: UUID,
    value: Optional[float],
    value_qualifier: Optional[str],
) -> Optional[dict]:
    edf = ElectricDecarbFactor.__table__
    res = await db.execute(select(edf.c.dataset_revision_id).where(edf.c.id == factor_id))
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(edf).where(edf.c.id == factor_id).values(
            value=value, value_qualifier=value_qualifier
        )
    )
    await db.commit()
    rows = await list_electric_decarb_factors(db, dataset_revision_id=row[0], skip=0, limit=10000)
    for r in rows:
        if str(r["id"]) == str(factor_id):
            return r
    return None


async def create_decarb_series(
    db: AsyncSession,
    dataset_revision_id: UUID,
    factor_type_code: str,
    jurisdiction_id: UUID,
    region_id: Optional[UUID],
    year_from: int,
    year_to: int,
) -> List[dict]:
    status = await _get_revision_status(db, dataset_revision_id)
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    edf = ElectricDecarbFactor.__table__
    where = [
        edf.c.dataset_revision_id == dataset_revision_id,
        edf.c.factor_type_code == factor_type_code,
        edf.c.jurisdiction_id == jurisdiction_id,
    ]
    if region_id is not None:
        where.append(edf.c.region_id == region_id)
    else:
        where.append(edf.c.region_id.is_(None))
    existing_res = await db.execute(select(edf.c.year).where(*where))
    existing_years = {r[0] for r in existing_res.fetchall()}
    for year in range(year_from, year_to + 1):
        if year not in existing_years:
            await db.execute(
                edf.insert().values(
                    dataset_revision_id=dataset_revision_id,
                    factor_type_code=factor_type_code,
                    jurisdiction_id=jurisdiction_id,
                    region_id=region_id,
                    year=year,
                    value=None,
                    value_qualifier=None,
                )
            )
    await db.commit()
    all_rows = await list_electric_decarb_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        factor_type_code=factor_type_code,
        skip=0,
        limit=10000,
    )
    if region_id is not None:
        return [r for r in all_rows if r["region_id"] is not None and str(r["region_id"]) == str(region_id)]
    return [r for r in all_rows if r["region_id"] is None]
