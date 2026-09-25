import uuid as _uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from core.base import Base


class UserGuideVideo(Base):
    __tablename__ = "user_guide_videos"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    title = Column(
        String(255),
        nullable=False,
    )

    youtube_url = Column(
        Text,
        nullable=False,
    )

    youtube_video_id = Column(
        String(50),
        nullable=False,
    )

    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    is_published = Column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin",
    )