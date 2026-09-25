from typing import List
from uuid import UUID
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, require_role
from core.security import Principal, get_current_principal
from core.session import get_session

from crud import user_guide_videos as crud
from schemas.user_guide_videos import (
    UserGuideVideoCreate,
    UserGuideVideoOut,
    UserGuideVideoResponse,
)

def extract_youtube_video_id(url: str) -> str:
    parsed = urlparse(url)

    if parsed.netloc in (
        "youtube.com",
        "www.youtube.com",
    ):
        video_id = parse_qs(parsed.query).get("v")

        if not video_id:
            raise ValueError("Invalid YouTube URL")

        return video_id[0]

    if parsed.netloc in (
        "youtu.be",
        "www.youtu.be",
    ):
        return parsed.path.strip("/")

    raise ValueError("Only YouTube URLs are supported")

router = APIRouter(
    prefix="/api/user-guide-videos",
    tags=["user-guide-videos"],
)

@router.get("/", response_model=List[UserGuideVideoOut])
async def get_published_videos(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    return await crud.get_published(db)

@router.get("/all", response_model=List[UserGuideVideoOut])
async def get_all_videos(
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    return await crud.get_all(db)

@router.post(
    "/",
    response_model=UserGuideVideoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_video(
    payload: UserGuideVideoCreate,
    _: None = Depends(require_role(SUPER_ADMIN)),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    try:
        youtube_video_id = extract_youtube_video_id(
            payload.youtube_url
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid YouTube URL is required.",
        )

    record = await crud.create_video(
        db,
        title=payload.title,
        youtube_url=payload.youtube_url,
        youtube_video_id=youtube_video_id,
        created_by_id=principal.user_id,
    )

    await db.commit()
    await db.refresh(record)

    return record

@router.put(
    "/{video_id}/publish",
    response_model=UserGuideVideoOut,
)
async def publish_video(
    video_id: UUID,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.publish_video(
        db,
        video_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    await db.commit()

    return record

@router.put(
    "/{video_id}/unpublish",
    response_model=UserGuideVideoOut,
)
async def unpublish_video(
    video_id: UUID,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    record = await crud.unpublish_video(
        db,
        video_id,
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    await db.commit()

    return record

@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_video(
    video_id: UUID,
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    deleted = await crud.delete_video(
        db,
        video_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    await db.commit()