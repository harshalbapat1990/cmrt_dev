from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from models.carbon_values import CarbonValue
from models.carbon_value_ranges import CarbonValueRange
from models.jurisdictions import Jurisdiction
from models.dataset_revisions import DatasetRevision


async def list_carbon_values(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    jurisdiction_id: Optional[UUID] = None,
    range_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 5000,
) -> List[dict]:
    jur_alias = Jurisdiction.__table__.alias("jur")
    cvr_alias = CarbonValueRange.__table__.alias("cvr")
    cv = CarbonValue.__table__

    q = (
        select(
            cv.c.id,
            cv.c.dataset_revision_id,
            cv.c.jurisdiction_id,
            jur_alias.c.name.label("jurisdiction_name"),
            cv.c.range_code,
            cvr_alias.c.name.label("range_name"),
            cv.c.year,
            cv.c.value,
            cv.c.currency,
            cv.c.source,
        )
        .select_from(
            cv
            .join(cvr_alias, cv.c.range_code == cvr_alias.c.code)
            .join(jur_alias, cv.c.jurisdiction_id == jur_alias.c.id)
        )
        .order_by(jur_alias.c.name, cvr_alias.c.code, cv.c.year)
    )

    if dataset_revision_id is not None:
        q = q.where(cv.c.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(cv.c.jurisdiction_id == jurisdiction_id)
    if range_code is not None:
        q = q.where(cv.c.range_code == range_code)

    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _get_revision_status(db: AsyncSession, revision_id: UUID) -> Optional[str]:
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == revision_id))
    return res.scalar_one_or_none()


async def update_carbon_value(
    db: AsyncSession,
    value_id: UUID,
    value: Optional[float],
    currency: Optional[str],
    source: Optional[str],
) -> Optional[dict]:
    cv = CarbonValue.__table__
    res = await db.execute(select(cv.c.dataset_revision_id).where(cv.c.id == value_id))
    row = res.first()
    if row is None:
        return None
    status = await _get_revision_status(db, row[0])
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")
    await db.execute(
        sa_update(cv).where(cv.c.id == value_id).values(
            value=value, currency=currency, source=source
        )
    )
    await db.commit()
    rows = await list_carbon_values(db, dataset_revision_id=row[0], skip=0, limit=10000)
    for r in rows:
        if str(r["id"]) == str(value_id):
            return r
    return None


async def create_carbon_value_series(
    db: AsyncSession,
    dataset_revision_id: UUID,
    jurisdiction_id: UUID,
    range_code: str,
    year_from: int,
    year_to: int,
) -> List[dict]:
    """Create a series of carbon values for a jurisdiction/range across a year range."""
    dr = DatasetRevision.__table__
    res = await db.execute(select(dr.c.status).where(dr.c.id == dataset_revision_id))
    status = res.scalar_one_or_none()
    if status != "draft":
        raise ValueError("Dataset revision is not in draft status and cannot be edited.")

    created_ids = []
    for year in range(year_from, year_to + 1):
        # Check if record already exists
        existing = await db.execute(
            select(CarbonValue).where(
                (CarbonValue.dataset_revision_id == dataset_revision_id) &
                (CarbonValue.jurisdiction_id == jurisdiction_id) &
                (CarbonValue.range_code == range_code) &
                (CarbonValue.year == year)
            )
        )
        if existing.scalars().first() is None:
            cv = CarbonValue(
                dataset_revision_id=dataset_revision_id,
                jurisdiction_id=jurisdiction_id,
                range_code=range_code,
                year=year,
                value=None,
                currency=None,
                source=None,
            )
            db.add(cv)
            created_ids.append(cv.id)

    await db.commit()

    # Return the created/updated records
    rows = await list_carbon_values(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        range_code=range_code,
    )
    return rows
