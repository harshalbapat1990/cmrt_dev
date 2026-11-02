from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.proponent_assumption_overrides import ProponentAssumptionOverride
from schemas.proponent_assumption_overrides import (
    ProponentAssumptionOverrideCreate,
    ProponentAssumptionOverrideUpdate,
)


async def create_proponent_assumption_override(
    db: AsyncSession, payload: ProponentAssumptionOverrideCreate
) -> ProponentAssumptionOverride:
    obj = ProponentAssumptionOverride(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_proponent_assumption_override(
    db: AsyncSession, override_id: UUID
) -> Optional[ProponentAssumptionOverride]:
    result = await db.execute(
        select(ProponentAssumptionOverride).where(ProponentAssumptionOverride.id == override_id)
    )
    return result.scalars().first()


async def get_proponent_assumption_override_by_key(
    db: AsyncSession, proponent_org_id: UUID, assumption_id: UUID, effective_from
) -> Optional[ProponentAssumptionOverride]:
    result = await db.execute(
        select(ProponentAssumptionOverride).where(
            ProponentAssumptionOverride.proponent_org_id == proponent_org_id,
            ProponentAssumptionOverride.assumption_id == assumption_id,
            ProponentAssumptionOverride.effective_from == effective_from,
        )
    )
    return result.scalars().first()


async def list_proponent_assumption_overrides(
    db: AsyncSession,
    proponent_org_id: Optional[UUID] = None,
    assumption_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[ProponentAssumptionOverride]:
    q = select(ProponentAssumptionOverride).order_by(
        ProponentAssumptionOverride.proponent_org_id,
        ProponentAssumptionOverride.effective_from,
    )
    if proponent_org_id is not None:
        q = q.where(ProponentAssumptionOverride.proponent_org_id == proponent_org_id)
    if assumption_id is not None:
        q = q.where(ProponentAssumptionOverride.assumption_id == assumption_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_proponent_assumption_override(
    db: AsyncSession, obj: ProponentAssumptionOverride, payload: ProponentAssumptionOverrideUpdate
) -> ProponentAssumptionOverride:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_proponent_assumption_override(db: AsyncSession, override_id: UUID) -> bool:
    obj = await get_proponent_assumption_override(db, override_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
