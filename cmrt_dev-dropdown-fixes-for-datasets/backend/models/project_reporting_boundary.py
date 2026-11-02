import uuid as _uuid

from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class ProjectReportingBoundary(Base):
    __tablename__ = "project_reporting_boundary"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_or_activity = Column(String(100), nullable=False)
    category = Column(String(500), nullable=False)
    sub_category = Column(String(500), nullable=False)
    source = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(
        TIMESTAMP(timezone=False), nullable=False, server_default=func.now()
    )
