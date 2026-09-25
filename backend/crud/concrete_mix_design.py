"""CRUD helpers for the BAU concrete mix designs dataset."""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.concrete_mix_design import (
    CALCULATED_COMPONENT_DEFINITIONS,
    INPUT_COMPONENT_DEFINITIONS,
    STRENGTH_FIELDS,
    TOTAL_CEMENTITIOUS_CODE,
    ConcreteMixAssumption,
    ConcreteMixDesign,
)


# ── Assumptions ─────────────────────────────────────────────────────────────

async def get_assumptions(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> Optional[ConcreteMixAssumption]:
    
    q = select(ConcreteMixAssumption).where(ConcreteMixAssumption.is_active.is_(True))
    if dataset_revision_id is None:
        q = q.where(ConcreteMixAssumption.dataset_revision_id.is_(None))
    else:
        q = q.where(ConcreteMixAssumption.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q)
    return result.scalars().first()


async def ensure_assumptions(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> ConcreteMixAssumption:
   
    obj = await get_assumptions(db, dataset_revision_id)
    if obj is not None:
        return obj
    obj = ConcreteMixAssumption(dataset_revision_id=dataset_revision_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_assumptions(
    db: AsyncSession,
    obj: ConcreteMixAssumption,
    patch: dict,
) -> ConcreteMixAssumption:
    for k, v in patch.items():
        setattr(obj, k, v)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


# ── Mix design rows ─────────────────────────────────────────────────────────

async def list_mix_designs(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> List[ConcreteMixDesign]:
    q = (
        select(ConcreteMixDesign)
        .where(ConcreteMixDesign.is_active.is_(True))
        .order_by(ConcreteMixDesign.display_order, ConcreteMixDesign.component_label)
    )
    if dataset_revision_id is None:
        q = q.where(ConcreteMixDesign.dataset_revision_id.is_(None))
    else:
        q = q.where(ConcreteMixDesign.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def ensure_mix_designs(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> List[ConcreteMixDesign]:
   
    rows = await list_mix_designs(db, dataset_revision_id)
    existing_codes = {r.component_code.lower() for r in rows}

    canonical = INPUT_COMPONENT_DEFINITIONS + CALCULATED_COMPONENT_DEFINITIONS
    missing = [defn for defn in canonical if defn[0].lower() not in existing_codes]
    if missing:
        for code, label, order in missing:
            db.add(
                ConcreteMixDesign(
                    dataset_revision_id=dataset_revision_id,
                    component_code=code,
                    component_label=label,
                    display_order=order,
                )
            )
        await db.flush()

    await recompute_calculated_rows(db, dataset_revision_id)

    return await list_mix_designs(db, dataset_revision_id)


def _calc_strengths(
    code: str,
    bau_scm: Optional[Decimal],
    max_fly_ash: Optional[Decimal],
    total_row: Optional[ConcreteMixDesign],
) -> dict:
    
    out: dict = {field: None for field in STRENGTH_FIELDS}
    if bau_scm is None or max_fly_ash is None or total_row is None:
        return out
    for field in STRENGTH_FIELDS:
        total = getattr(total_row, field)
        if total is None:
            continue
        if code == "general_purpose_cement":
            out[field] = (Decimal("1") - bau_scm) * total
        elif code == "fly_ash":
            out[field] = (bau_scm if bau_scm < max_fly_ash else max_fly_ash) * total
        elif code == "ggbf_slag":
            out[field] = (
                (bau_scm - max_fly_ash) * total
                if bau_scm > max_fly_ash
                else Decimal("0")
            )
    return out


async def recompute_calculated_rows(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
) -> List[ConcreteMixDesign]:
    
    assumptions = await get_assumptions(db, dataset_revision_id)
    bau_scm = assumptions.bau_scm_content_pct if assumptions else None
    max_fly_ash = assumptions.default_max_fly_ash_pct if assumptions else None

    rows = await list_mix_designs(db, dataset_revision_id)
    by_code = {r.component_code: r for r in rows}
    total_row = by_code.get(TOTAL_CEMENTITIOUS_CODE)

    updated: List[ConcreteMixDesign] = []
    for code, label, order in CALCULATED_COMPONENT_DEFINITIONS:
        target = by_code.get(code)
        if target is None:
            target = ConcreteMixDesign(
                dataset_revision_id=dataset_revision_id,
                component_code=code,
                component_label=label,
                display_order=order,
            )
            db.add(target)
        new_strengths = _calc_strengths(code, bau_scm, max_fly_ash, total_row)
        for field, value in new_strengths.items():
            setattr(target, field, value)
        updated.append(target)

    await db.flush()
    for r in updated:
        await db.refresh(r)
    return updated


async def get_mix_design(
    db: AsyncSession,
    record_id: UUID,
) -> Optional[ConcreteMixDesign]:
    result = await db.execute(
        select(ConcreteMixDesign).where(ConcreteMixDesign.id == record_id)
    )
    return result.scalars().first()


async def update_mix_design(
    db: AsyncSession,
    obj: ConcreteMixDesign,
    patch: dict,
) -> ConcreteMixDesign:
    for k, v in patch.items():
        setattr(obj, k, v)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj
