from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.base_case_assumptions import BaseCaseAssumption
from schemas.base_case_assumptions import BaseCaseAssumptionCreate, BaseCaseAssumptionUpdate


async def create_base_case_assumption(
    db: AsyncSession, payload: BaseCaseAssumptionCreate
) -> BaseCaseAssumption:
    obj = BaseCaseAssumption(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_base_case_assumption(
    db: AsyncSession, assumption_id: UUID
) -> Optional[BaseCaseAssumption]:
    result = await db.execute(
        select(BaseCaseAssumption).where(BaseCaseAssumption.id == assumption_id)
    )
    return result.scalars().first()


async def get_base_case_assumption_by_category_name(
    db: AsyncSession, emissions_category_id: UUID, name: str
) -> Optional[BaseCaseAssumption]:
    result = await db.execute(
        select(BaseCaseAssumption).where(
            BaseCaseAssumption.emissions_category_id == emissions_category_id,
            BaseCaseAssumption.name == name,
        )
    )
    return result.scalars().first()


async def list_base_case_assumptions(
    db: AsyncSession,
    emissions_category_id: Optional[UUID] = None,
    is_anz_default: Optional[bool] = None,
    dataset_revision_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[BaseCaseAssumption]:
    q = select(BaseCaseAssumption).order_by(BaseCaseAssumption.emissions_category_id, BaseCaseAssumption.name)
    if emissions_category_id is not None:
        q = q.where(BaseCaseAssumption.emissions_category_id == emissions_category_id)
    if is_anz_default is not None:
        q = q.where(BaseCaseAssumption.is_anz_default == is_anz_default)
    if dataset_revision_id is not None:
        q = q.where(BaseCaseAssumption.dataset_revision_id == dataset_revision_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def update_base_case_assumption(
    db: AsyncSession, obj: BaseCaseAssumption, payload: BaseCaseAssumptionUpdate
) -> BaseCaseAssumption:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_base_case_assumption(db: AsyncSession, assumption_id: UUID) -> bool:
    obj = await get_base_case_assumption(db, assumption_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
