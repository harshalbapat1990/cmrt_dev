from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserGuideVideoCreate(BaseModel):
    title: str
    youtube_url: str


class UserGuideVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    youtube_url: str
    youtube_video_id: str
    created_by_id: Optional[UUID] = None
    created_at: datetime
    is_published: bool


class UserGuideVideoResponse(UserGuideVideoOut):
    pass