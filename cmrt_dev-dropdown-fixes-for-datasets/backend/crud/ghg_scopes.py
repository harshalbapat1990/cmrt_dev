from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.ghg_scopes import GhgScope


async def get_ghg_scope(db: AsyncSession, scope_id: int) -> Optional[GhgScope]:
    result = await db.execute(select(GhgScope).where(GhgScope.id == scope_id))
    return result.scalars().first()


async def list_ghg_scopes(db: AsyncSession) -> List[GhgScope]:
    result = await db.execute(select(GhgScope).order_by(GhgScope.id))
    return result.scalars().all()
