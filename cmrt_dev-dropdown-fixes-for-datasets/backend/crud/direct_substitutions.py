from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.direct_substitution_factors import DirectSubstitutionFactor
from schemas.direct_substitutions import DirectSubstitutionCreate, DirectSubstitutionUpdate, DirectSubstitutionUpsert


async def list_direct_substitutions(
    db: AsyncSession,
    dataset_revision_id: UUID,
    jurisdiction_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[DirectSubstitutionFactor], int]:
    count_stmt = select(func.count()).select_from(DirectSubstitutionFactor)
    count_stmt = count_stmt.where(DirectSubstitutionFactor.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        count_stmt = count_stmt.where(DirectSubstitutionFactor.jurisdiction_id == jurisdiction_id)
    total = int((await db.execute(count_stmt)).scalar() or 0)

    q = select(DirectSubstitutionFactor)
    q = q.where(DirectSubstitutionFactor.dataset_revision_id == dataset_revision_id)
    if jurisdiction_id is not None:
        q = q.where(DirectSubstitutionFactor.jurisdiction_id == jurisdiction_id)
    q = (
        q.order_by(
            DirectSubstitutionFactor.jurisdiction_id,
            DirectSubstitutionFactor.display_order,
            DirectSubstitutionFactor.user_emissions_source,
        )
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(q)
    rows = list(res.scalars().unique().all())
    return rows, total


async def get_direct_substitution(
    db: AsyncSession, factor_id: UUID
) -> Optional[DirectSubstitutionFactor]:
    res = await db.execute(
        select(DirectSubstitutionFactor).where(DirectSubstitutionFactor.id == factor_id)
    )
    return res.scalars().first()


async def create_direct_substitution(
    db: AsyncSession, payload: DirectSubstitutionCreate, jurisdiction_id: UUID
) -> DirectSubstitutionFactor:
    body = payload.model_dump(
        exclude={"dataset_revision_id", "jurisdiction_id", "jurisdiction_name"},
        exclude_none=True,
    )
    obj = DirectSubstitutionFactor(
        dataset_revision_id=payload.dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        **body,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_direct_substitution(
    db: AsyncSession,
    obj: DirectSubstitutionFactor,
    payload: DirectSubstitutionUpdate,
) -> DirectSubstitutionFactor:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def upsert_direct_substitution(
    db: AsyncSession,
    payload: DirectSubstitutionUpsert,
    jurisdiction_id: UUID,
) -> DirectSubstitutionFactor:
    stmt = (
        select(DirectSubstitutionFactor)
        .where(
            DirectSubstitutionFactor.dataset_revision_id == payload.dataset_revision_id,
            DirectSubstitutionFactor.jurisdiction_id == jurisdiction_id,
            DirectSubstitutionFactor.user_emissions_source == payload.user_emissions_source,
            DirectSubstitutionFactor.user_unit == payload.user_unit,
            DirectSubstitutionFactor.bau_equivalent_emission_source
            == payload.bau_equivalent_emission_source,
            DirectSubstitutionFactor.bau_equivalent_unit == payload.bau_equivalent_unit,
        )
        .order_by(DirectSubstitutionFactor.id)
    )
    res = await db.execute(stmt)
    matches = list(res.scalars().all())

    if len(matches) > 1:
        primary = matches[0]
        for dup in matches[1:]:
            await db.delete(dup)
        await db.flush()
        existing = primary
    elif len(matches) == 1:
        existing = matches[0]
    else:
        existing = None

    if existing:
        existing.user_emissions_source = payload.user_emissions_source
        existing.user_unit = payload.user_unit
        existing.bau_equivalent_emission_source = payload.bau_equivalent_emission_source
        existing.bau_equivalent_unit = payload.bau_equivalent_unit
        existing.bau_quantity_per_user_unit = payload.bau_quantity_per_user_unit
        if payload.display_order is not None:
            existing.display_order = payload.display_order
        db.add(existing)
        await db.flush()
        await db.refresh(existing)
        return existing

    display_order = payload.display_order if payload.display_order is not None else 0
    obj = DirectSubstitutionFactor(
        dataset_revision_id=payload.dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        user_emissions_source=payload.user_emissions_source,
        user_unit=payload.user_unit,
        bau_equivalent_emission_source=payload.bau_equivalent_emission_source,
        bau_equivalent_unit=payload.bau_equivalent_unit,
        bau_quantity_per_user_unit=payload.bau_quantity_per_user_unit,
        display_order=display_order,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj
