from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_guide_videos import UserGuideVideo


async def get_published(db: AsyncSession) -> List[UserGuideVideo]:
    result = await db.execute(
        select(UserGuideVideo)
        .where(UserGuideVideo.is_published == True)
        .order_by(UserGuideVideo.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all(db: AsyncSession) -> List[UserGuideVideo]:
    result = await db.execute(
        select(UserGuideVideo)
        .order_by(UserGuideVideo.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(
    db: AsyncSession,
    video_id: UUID,
    ) -> Optional[UserGuideVideo]:
    result = await db.execute(
        select(UserGuideVideo)
        .where(UserGuideVideo.id == video_id)
    )
    return result.scalars().first()


async def create_video(
    db: AsyncSession,
    *,
    title: str,
    youtube_url: str,
    youtube_video_id: str,
    created_by_id: Optional[UUID],
) -> UserGuideVideo:
    record = UserGuideVideo(
        title=title,
        youtube_url=youtube_url,
        youtube_video_id=youtube_video_id,
        created_by_id=created_by_id,
        is_published=False,
    )

    db.add(record)
    await db.flush()
    await db.refresh(record)

    return record


async def publish_video(
    db: AsyncSession,
    video_id: UUID,
    ) -> Optional[UserGuideVideo]:
    record = await get_by_id(db, video_id)

    if record is None:
        return None

    record.is_published = True

    db.add(record)
    await db.flush()
    await db.refresh(record)

    return record


async def unpublish_video(
    db: AsyncSession,
    video_id: UUID,
    ) -> Optional[UserGuideVideo]:
    record = await get_by_id(db, video_id)

    if record is None:
        return None

    record.is_published = False

    db.add(record)
    await db.flush()
    await db.refresh(record)

    return record


async def delete_video(
    db: AsyncSession,
    video_id: UUID,
) -> bool:
    record = await get_by_id(db, video_id)

    if record is None:
        return False

    await db.delete(record)

    return True