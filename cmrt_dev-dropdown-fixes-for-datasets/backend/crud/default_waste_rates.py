from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.default_waste_rates import DefaultWasteRate
from models.jurisdictions import Jurisdiction
from models.materials import Material
from models.waste_treatments import WasteTreatment
from schemas.default_waste_rates import DefaultWasteRateCreate, DefaultWasteRateUpdate


async def create_default_waste_rate(
    db: AsyncSession, payload: DefaultWasteRateCreate
) -> DefaultWasteRate:
    obj = DefaultWasteRate(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_default_waste_rate(db: AsyncSession, record_id: UUID) -> Optional[DefaultWasteRate]:
    result = await db.execute(
        select(DefaultWasteRate).where(DefaultWasteRate.id == record_id)
    )
    return result.scalars().first()


async def get_default_waste_rate_by_key(
    db: AsyncSession,
    jurisdiction_id: UUID,
    material_id: UUID,
    waste_treatment_id: UUID,
    applicable_lifecycle_module_code: Optional[str],
    basis: str,
) -> Optional[DefaultWasteRate]:
    q = select(DefaultWasteRate).where(
        DefaultWasteRate.jurisdiction_id == jurisdiction_id,
        DefaultWasteRate.material_id == material_id,
        DefaultWasteRate.waste_treatment_id == waste_treatment_id,
        DefaultWasteRate.basis == basis,
        DefaultWasteRate.is_active.is_(True),
    )
    if applicable_lifecycle_module_code is None:
        q = q.where(DefaultWasteRate.applicable_lifecycle_module_code.is_(None))
    else:
        q = q.where(DefaultWasteRate.applicable_lifecycle_module_code == applicable_lifecycle_module_code)
    result = await db.execute(q)
    return result.scalars().first()


async def list_default_waste_rates(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    waste_treatment_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DefaultWasteRate]:
    q = select(DefaultWasteRate).where(DefaultWasteRate.is_active.is_(True))
    if jurisdiction_id is not None:
        q = q.where(DefaultWasteRate.jurisdiction_id == jurisdiction_id)
    if material_id is not None:
        q = q.where(DefaultWasteRate.material_id == material_id)
    if waste_treatment_id is not None:
        q = q.where(DefaultWasteRate.waste_treatment_id == waste_treatment_id)
    if dataset_revision_id is not None:
        q = q.where(DefaultWasteRate.dataset_revision_id == dataset_revision_id)
    if as_of_date is not None:
        q = q.where(
            (DefaultWasteRate.effective_from.is_(None))
            | (DefaultWasteRate.effective_from <= as_of_date)
        ).where(
            (DefaultWasteRate.effective_to.is_(None))
            | (DefaultWasteRate.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_default_waste_rate(
    db: AsyncSession, obj: DefaultWasteRate, payload: DefaultWasteRateUpdate
) -> DefaultWasteRate:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_default_waste_rate(db: AsyncSession, record_id: UUID) -> bool:
    obj = await get_default_waste_rate(db, record_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def supersede_default_waste_rate(
    db: AsyncSession,
    old_obj: DefaultWasteRate,
    payload: dict,
) -> DefaultWasteRate:
    old_obj.is_active = False
    db.add(old_obj)
    skip_cols = {"id", "is_active"}
    data = {
        c.name: getattr(old_obj, c.name)
        for c in DefaultWasteRate.__table__.columns
        if c.name not in skip_cols
    }
    data.update(payload)
    new_obj = DefaultWasteRate(**data, is_active=True)
    db.add(new_obj)
    await db.flush()
    await db.refresh(new_obj)
    return new_obj


async def get_default_waste_rate_with_names(
    db: AsyncSession, record_id: UUID
) -> Optional[Dict[str, Any]]:
    q = (
        select(
            DefaultWasteRate,
            Material.name.label("material_name"),
            WasteTreatment.name.label("waste_treatment_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, DefaultWasteRate.material_id == Material.id)
        .outerjoin(WasteTreatment, DefaultWasteRate.waste_treatment_id == WasteTreatment.id)
        .outerjoin(Jurisdiction, DefaultWasteRate.jurisdiction_id == Jurisdiction.id)
        .where(DefaultWasteRate.id == record_id)
    )
    result = await db.execute(q)
    row = result.first()
    if row is None:
        return None
    dwr: DefaultWasteRate = row[0]
    return {
        "id": dwr.id,
        "jurisdiction_id": dwr.jurisdiction_id,
        "material_id": dwr.material_id,
        "waste_treatment_id": dwr.waste_treatment_id,
        "applicable_lifecycle_module_code": dwr.applicable_lifecycle_module_code,
        "basis": dwr.basis,
        "rate": dwr.rate,
        "rate_unit_id": dwr.rate_unit_id,
        "notes": dwr.notes,
        "effective_from": dwr.effective_from,
        "effective_to": dwr.effective_to,
        "is_active": dwr.is_active,
        "material_name": row.material_name,
        "waste_treatment_name": row.waste_treatment_name,
        "jurisdiction_name": row.jurisdiction_name,
    }


async def list_default_waste_rates_with_names(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID] = None,
    material_id: Optional[UUID] = None,
    waste_treatment_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    q = (
        select(
            DefaultWasteRate,
            Material.name.label("material_name"),
            WasteTreatment.name.label("waste_treatment_name"),
            Jurisdiction.name.label("jurisdiction_name"),
        )
        .outerjoin(Material, DefaultWasteRate.material_id == Material.id)
        .outerjoin(WasteTreatment, DefaultWasteRate.waste_treatment_id == WasteTreatment.id)
        .outerjoin(Jurisdiction, DefaultWasteRate.jurisdiction_id == Jurisdiction.id)
        .where(DefaultWasteRate.is_active.is_(True))
    )
    if jurisdiction_id is not None:
        q = q.where(DefaultWasteRate.jurisdiction_id == jurisdiction_id)
    if material_id is not None:
        q = q.where(DefaultWasteRate.material_id == material_id)
    if waste_treatment_id is not None:
        q = q.where(DefaultWasteRate.waste_treatment_id == waste_treatment_id)
    if dataset_revision_id is not None:
        q = q.where(DefaultWasteRate.dataset_revision_id == dataset_revision_id)
    if as_of_date is not None:
        q = q.where(
            (DefaultWasteRate.effective_from.is_(None))
            | (DefaultWasteRate.effective_from <= as_of_date)
        ).where(
            (DefaultWasteRate.effective_to.is_(None))
            | (DefaultWasteRate.effective_to >= as_of_date)
        )
    result = await db.execute(q.offset(skip).limit(limit))
    rows = result.all()
    out: List[Dict[str, Any]] = []
    for row in rows:
        dwr: DefaultWasteRate = row[0]
        out.append({
            "id": dwr.id,
            "jurisdiction_id": dwr.jurisdiction_id,
            "material_id": dwr.material_id,
            "waste_treatment_id": dwr.waste_treatment_id,
            "applicable_lifecycle_module_code": dwr.applicable_lifecycle_module_code,
            "basis": dwr.basis,
            "rate": dwr.rate,
            "rate_unit_id": dwr.rate_unit_id,
            "notes": dwr.notes,
            "effective_from": dwr.effective_from,
            "effective_to": dwr.effective_to,
            "is_active": dwr.is_active,
            "material_name": row.material_name,
            "waste_treatment_name": row.waste_treatment_name,
            "jurisdiction_name": row.jurisdiction_name,
        })
    return out
