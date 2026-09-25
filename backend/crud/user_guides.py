from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_guides import UserGuide


async def get_next_version(db: AsyncSession) -> int:
    result = await db.execute(select(UserGuide.version))
    versions = result.scalars().all()
    return (max(versions) + 1) if versions else 1


async def deactivate_all(db: AsyncSession) -> None:
    await db.execute(update(UserGuide).values(is_active=False))


async def create_version(
    db: AsyncSession,
    *,
    filename: str,
    file_size: int,
    uploaded_by_id: Optional[UUID],
) -> UserGuide:
    version = await get_next_version(db)
    await deactivate_all(db)

    record = UserGuide(
        version=version,
        filename=filename,
        file_size=file_size,
        uploaded_by_id=uploaded_by_id,
        is_active=True,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_active(db: AsyncSession) -> Optional[UserGuide]:
    result = await db.execute(
        select(UserGuide).where(UserGuide.is_active == True).limit(1)
    )
    return result.scalars().first()


async def get_all_versions(db: AsyncSession) -> List[UserGuide]:
    result = await db.execute(
        select(UserGuide).order_by(UserGuide.version.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, guide_id: UUID) -> Optional[UserGuide]:
    result = await db.execute(
        select(UserGuide).where(UserGuide.id == guide_id)
    )
    return result.scalars().first()


async def activate_version(db: AsyncSession, guide_id: UUID) -> Optional[UserGuide]:
    record = await get_by_id(db, guide_id)
    if record is None:
        return None
    await deactivate_all(db)
    record.is_active = True
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record
