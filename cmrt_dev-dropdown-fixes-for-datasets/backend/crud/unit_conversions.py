from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.unit_conversions import UnitConversion
from models.units import Unit
from schemas.unit_conversions import UnitConversionCreate, UnitConversionUpdate


async def create_unit_conversion(db: AsyncSession, payload: UnitConversionCreate) -> UnitConversion:
    obj = UnitConversion(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_unit_conversion(db: AsyncSession, conversion_id: UUID) -> Optional[UnitConversion]:
    result = await db.execute(select(UnitConversion).where(UnitConversion.id == conversion_id))
    return result.scalars().first()


async def get_unit_conversion_by_pair(
    db: AsyncSession,
    from_unit_id: UUID,
    to_unit_id: UUID,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[UnitConversion]:
    query = select(UnitConversion).where(
        UnitConversion.from_unit_id == from_unit_id,
        UnitConversion.to_unit_id == to_unit_id,
    )
    if dataset_revision_id is None:
        query = query.where(UnitConversion.dataset_revision_id.is_(None))
    else:
        query = query.where(UnitConversion.dataset_revision_id == dataset_revision_id)
    result = await db.execute(query)
    return result.scalars().first()


async def list_unit_conversions(
    db: AsyncSession,
    from_unit_id: Optional[UUID] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    global_only: bool = False,
) -> List[UnitConversion]:
    query = select(UnitConversion)
    if from_unit_id is not None:
        query = query.where(UnitConversion.from_unit_id == from_unit_id)
    if dataset_revision_id is not None:
        query = query.where(UnitConversion.dataset_revision_id == dataset_revision_id)
    elif global_only:
        query = query.where(UnitConversion.dataset_revision_id.is_(None))
    # When neither is provided, return all rows (no revision filter)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_unit_conversion(
    db: AsyncSession, obj: UnitConversion, payload: UnitConversionUpdate
) -> UnitConversion:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_unit_conversion(db: AsyncSession, conversion_id: UUID) -> bool:
    obj = await get_unit_conversion(db, conversion_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def get_conversion_factor(
    db: AsyncSession,
    from_unit_id: UUID,
    to_unit_id: UUID,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[Decimal]:
    if from_unit_id == to_unit_id:
        return Decimal("1")
    conv = None
    if dataset_revision_id is not None:
        conv = await get_unit_conversion_by_pair(db, from_unit_id, to_unit_id, dataset_revision_id)
    if conv is None:
        conv = await get_unit_conversion_by_pair(db, from_unit_id, to_unit_id, None)
    return Decimal(str(conv.factor)) if conv is not None else None


async def build_unit_options_with_conversions(
    db: AsyncSession,
    canonical_unit_ids: List[UUID],
    dataset_revision_id: Optional[UUID] = None,
) -> List[Dict[str, Any]]:
    if not canonical_unit_ids:
        return []

    canon_result = await db.execute(
        select(Unit)
        .where(Unit.id.in_(canonical_unit_ids))
        .order_by(Unit.code)
    )
    canon_units: list[Unit] = list(canon_result.scalars().all())
    canonical_id_set = {u.id for u in canon_units}

    options: List[Dict[str, Any]] = [
        {
            "id": u.id,
            "name": u.code,
            "label": u.label,
            "is_canonical": True,
            "to_canonical_factor": 1,
            "canonical_unit_id": u.id,
            "canonical_unit_code": u.code,
        }
        for u in canon_units
    ]

    # Include conversions for the active dataset revision (if provided) AND global ones (null).
    conv_filter = UnitConversion.to_unit_id.in_(canonical_unit_ids)
    if dataset_revision_id is not None:
        from sqlalchemy import case, or_
        revision_filter = or_(
            UnitConversion.dataset_revision_id.is_(None),
            UnitConversion.dataset_revision_id == dataset_revision_id,
        )
        conv_result = await db.execute(
            select(UnitConversion)
            .where(conv_filter)
            .where(revision_filter)
            .order_by(
                case((UnitConversion.dataset_revision_id == dataset_revision_id, 0), else_=1),
                UnitConversion.to_unit_id,
                UnitConversion.from_unit_id,
            )
        )
    else:
        conv_result = await db.execute(
            select(UnitConversion)
            .where(conv_filter)
            .where(UnitConversion.dataset_revision_id.is_(None))
        )
    conversions: list[UnitConversion] = list(conv_result.scalars().all())

    if not conversions:
        return options

    from_unit_ids = {c.from_unit_id for c in conversions}
    unit_result = await db.execute(
        select(Unit)
        .where(Unit.id.in_(from_unit_ids))
    )
    source_units = {u.id: u for u in unit_result.scalars().all()}
    canonical_lookup = {u.id: u for u in canon_units}

    seen_non_canonical: set[UUID] = set()
    non_canonical: List[Dict[str, Any]] = []
    for conv in conversions:
        source_unit = source_units.get(conv.from_unit_id)
        canonical_unit = canonical_lookup.get(conv.to_unit_id)

        if source_unit is None or canonical_unit is None:
            continue
        if source_unit.id in seen_non_canonical:
            continue
        if source_unit.id in canonical_id_set:
            continue
        seen_non_canonical.add(source_unit.id)
        non_canonical.append(
            {
                "id": source_unit.id,
                "name": source_unit.code,
                "label": source_unit.label,
                "is_canonical": False,
                "to_canonical_factor": Decimal(str(conv.factor)),
                "canonical_unit_id": canonical_unit.id,
                "canonical_unit_code": canonical_unit.code,
            }
        )

    non_canonical.sort(key=lambda x: x["name"])
    return options + non_canonical
