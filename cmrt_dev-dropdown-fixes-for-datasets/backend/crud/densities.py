from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.densities import Density
from schemas.densities import DensityCreate, DensityUpdate, DensityOut


async def create_density(
    db: AsyncSession,
    payload: DensityCreate,
) -> DensityOut:
    obj = Density(**payload.model_dump())

    db.add(obj)
    await db.flush()
    await db.refresh(obj)

    return obj


async def get_density(
    db: AsyncSession,
    density_id: UUID,
) -> Density | None:
    result = await db.execute(
        select(Density).where(Density.id == density_id)
    )

    return result.scalars().first()


async def get_density_by_key(
    db: AsyncSession,
    jurisdiction_id: UUID,
    dataset: str,
    record_key: str,
    unit_id: UUID,
    dataset_revision_id: UUID,
) -> Density | None:
    query = select(Density).where(
        Density.dataset == dataset,
        Density.record_key == record_key,
        Density.unit_id == unit_id,
    )

    if jurisdiction_id is not None:
        query = query.where(
            Density.jurisdiction_id == jurisdiction_id
        )

    if dataset_revision_id is not None:
        query = query.where(
            Density.dataset_revision_id == dataset_revision_id
        )

    result = await db.execute(query)

    return result.scalars().first()


async def list_densities(
    db: AsyncSession,
    dataset: str | None = None,
    jurisdiction_id: UUID | None = None,
    unit_id: UUID | None = None,
    search: str | None = None,
    dataset_revision_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Density]:
    query = select(Density)

    if dataset is not None:
        query = query.where(Density.dataset == dataset)

    if jurisdiction_id is not None:
        query = query.where(
            Density.jurisdiction_id == jurisdiction_id
        )

    if unit_id is not None:
        query = query.where(Density.unit_id == unit_id)

    if dataset_revision_id is not None:
        query = query.where(
            Density.dataset_revision_id == dataset_revision_id
        )

    if search:
        like = f"%{search}%"

        query = query.where(
            Density.record_key.ilike(like)
            | Density.emissions_source.ilike(like)
        )

    query = (
        query.order_by(
            Density.dataset,
            Density.record_key,
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)

    return list(result.scalars().all())


async def update_density(
    db: AsyncSession,
    obj: Density,
    payload: DensityUpdate,
) -> Density:
    changes = payload.model_dump(exclude_unset=True)

    for field_name, value in changes.items():
        setattr(obj, field_name, value)

    await db.flush()
    await db.refresh(obj)

    return obj


async def delete_density(
    db: AsyncSession,
    density_id: UUID,
) -> bool:
    obj = await get_density(
        db=db,
        density_id=density_id,
    )

    if obj is None:
        return False

    await db.delete(obj)
    return True


async def density_exists(
    db: AsyncSession,
    density_id: UUID,
) -> bool:
    result = await db.execute(
        select(Density.id).where(
            Density.id == density_id
        )
    )

    return result.scalar_one_or_none() is not None
