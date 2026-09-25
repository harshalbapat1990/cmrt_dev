from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.default_transport_distances import DefaultTransportDistance
from models.materials import Material
from models.jurisdictions import Jurisdiction
from models.emissions_categories_new import EmissionsCategoryRecord
from schemas.default_transport_distances import DefaultTransportDistanceCreate, DefaultTransportDistanceUpdate


async def create_default_transport_distance(
    db: AsyncSession, payload: DefaultTransportDistanceCreate
) -> DefaultTransportDistance:
    obj = DefaultTransportDistance(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_default_transport_distance(
    db: AsyncSession, record_id: UUID
) -> Optional[DefaultTransportDistance]:
    result = await db.execute(
        select(DefaultTransportDistance).where(DefaultTransportDistance.id == record_id)
    )
    return result.scalars().first()


async def get_default_transport_distance_by_key(
    db: AsyncSession,
    jurisdiction_id: UUID,
    material_id: Optional[UUID],
    emissions_category_id: Optional[UUID],
) -> Optional[DefaultTransportDistance]:
    q = select(DefaultTransportDistance).where(
        DefaultTransportDistance.jurisdiction_id == jurisdiction_id,
        DefaultTransportDistance.is_active.is_(True),
    )
    if material_id is not None:
        q = q.where(DefaultTransportDistance.material_id == material_id)
    else:
        q = q.where(DefaultTransportDistance.material_id.is_(None))
    if emissions_category_id is not None:
        q = q.where(DefaultTransportDistance.emissions_category_id == emissions_category_id)
    else:
        q = q.where(DefaultTransportDistance.emissions_category_id.is_(None))
    result = await db.execute(q)
    return result.scalars().first()


async def list_default_transport_distances(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    emissions_category_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DefaultTransportDistance]:
    q = select(DefaultTransportDistance).where(
        DefaultTransportDistance.is_active.is_(True)
    ).order_by(DefaultTransportDistance.id)
    if jurisdiction_id is not None:
        q = q.where(DefaultTransportDistance.jurisdiction_id == jurisdiction_id)
    if material_id is not None:
        q = q.where(DefaultTransportDistance.material_id == material_id)
    if emissions_category_id is not None:
        q = q.where(DefaultTransportDistance.emissions_category_id == emissions_category_id)
    if dataset_revision_id is not None:
        q = q.where(
            (DefaultTransportDistance.dataset_revision_id == dataset_revision_id)
            | (DefaultTransportDistance.dataset_revision_id.is_(None))
        )
    if as_of_date is not None:
        q = q.where(
            (DefaultTransportDistance.effective_from.is_(None))
            | (DefaultTransportDistance.effective_from <= as_of_date)
        ).where(
            (DefaultTransportDistance.effective_to.is_(None))
            | (DefaultTransportDistance.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_default_transport_distance(
    db: AsyncSession, obj: DefaultTransportDistance, payload: DefaultTransportDistanceUpdate
) -> DefaultTransportDistance:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_default_transport_distance(db: AsyncSession, record_id: UUID) -> bool:
    obj = await get_default_transport_distance(db, record_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def supersede_default_transport_distance(
    db: AsyncSession,
    old_obj: DefaultTransportDistance,
    payload: dict,
) -> DefaultTransportDistance:
    old_obj.is_active = False
    db.add(old_obj)
    skip_cols = {"id", "is_active"}
    data = {
        c.name: getattr(old_obj, c.name)
        for c in DefaultTransportDistance.__table__.columns
        if c.name not in skip_cols
    }
    data.update(payload)
    new_obj = DefaultTransportDistance(**data, is_active=True)
    db.add(new_obj)
    await db.flush()
    await db.refresh(new_obj)
    return new_obj


async def get_default_transport_distance_with_names(
    db: AsyncSession, record_id: UUID
) -> Optional[Dict[str, Any]]:
    q = (
        select(
            DefaultTransportDistance,
            Material.name.label("material_name"),
            EmissionsCategoryRecord.name.label("emissions_category_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, DefaultTransportDistance.material_id == Material.id)
        .outerjoin(
            EmissionsCategoryRecord,
            DefaultTransportDistance.emissions_category_id == EmissionsCategoryRecord.id,
        )
        .outerjoin(Jurisdiction, DefaultTransportDistance.jurisdiction_id == Jurisdiction.id)
        .where(DefaultTransportDistance.id == record_id)
    )
    result = await db.execute(q)
    row = result.first()
    if row is None:
        return None
    dtd: DefaultTransportDistance = row[0]
    return {
        "id": dtd.id,
        "material_id": dtd.material_id,
        "emissions_category_id": dtd.emissions_category_id,
        "jurisdiction_id": dtd.jurisdiction_id,
        "truck_distance": dtd.truck_distance,
        "rail_distance": dtd.rail_distance,
        "sea_distance": dtd.sea_distance,
        "distance_unit_id": dtd.distance_unit_id,
        "truck_transport_mode": dtd.truck_transport_mode,
        "rail_transport_mode": dtd.rail_transport_mode,
        "sea_transport_mode": dtd.sea_transport_mode,
        "source": dtd.source,
        "grade_applicability": dtd.grade_applicability,
        "effective_from": dtd.effective_from,
        "effective_to": dtd.effective_to,
        "is_active": dtd.is_active,
        "material_name": row.material_name,
        "emissions_category_name": row.emissions_category_name,
        "jurisdiction_name": row.jurisdiction_name,
    }


async def list_default_transport_distances_with_names(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    emissions_category_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    q = (
        select(
            DefaultTransportDistance,
            Material.name.label("material_name"),
            EmissionsCategoryRecord.name.label("emissions_category_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, DefaultTransportDistance.material_id == Material.id)
        .outerjoin(
            EmissionsCategoryRecord,
            DefaultTransportDistance.emissions_category_id == EmissionsCategoryRecord.id,
        )
        .outerjoin(Jurisdiction, DefaultTransportDistance.jurisdiction_id == Jurisdiction.id)
        .where(DefaultTransportDistance.is_active.is_(True))
        .order_by(DefaultTransportDistance.id)
    )
    if jurisdiction_id is not None:
        q = q.where(DefaultTransportDistance.jurisdiction_id == jurisdiction_id)
    if material_id is not None:
        q = q.where(DefaultTransportDistance.material_id == material_id)
    if emissions_category_id is not None:
        q = q.where(DefaultTransportDistance.emissions_category_id == emissions_category_id)
    if dataset_revision_id is not None:
        q = q.where(
            (DefaultTransportDistance.dataset_revision_id == dataset_revision_id)
            | (DefaultTransportDistance.dataset_revision_id.is_(None))
        )
    if as_of_date is not None:
        q = q.where(
            (DefaultTransportDistance.effective_from.is_(None))
            | (DefaultTransportDistance.effective_from <= as_of_date)
        ).where(
            (DefaultTransportDistance.effective_to.is_(None))
            | (DefaultTransportDistance.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.all()
    out: List[Dict[str, Any]] = []
    for row in rows:
        dtd: DefaultTransportDistance = row[0]
        out.append({
            "id": dtd.id,
            "material_id": dtd.material_id,
            "emissions_category_id": dtd.emissions_category_id,
            "jurisdiction_id": dtd.jurisdiction_id,
            "truck_distance": dtd.truck_distance,
            "rail_distance": dtd.rail_distance,
            "sea_distance": dtd.sea_distance,
            "distance_unit_id": dtd.distance_unit_id,
            "truck_transport_mode": dtd.truck_transport_mode,
            "rail_transport_mode": dtd.rail_transport_mode,
            "sea_transport_mode": dtd.sea_transport_mode,
            "source": dtd.source,
            "grade_applicability": dtd.grade_applicability,
            "effective_from": dtd.effective_from,
            "effective_to": dtd.effective_to,
            "material_name": row.material_name,
            "emissions_category_name": row.emissions_category_name,
            "jurisdiction_name": row.jurisdiction_name,
        })
    return out
