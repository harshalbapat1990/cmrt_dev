import uuid as _uuid
from sqlalchemy import Boolean, Column, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class ProjectDatasetExclusion(Base):
    __tablename__ = "project_dataset_exclusions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    metric_id = Column(
        UUID(as_uuid=True),
        ForeignKey("background_grade_metrics.id"),
        nullable=False,
    )
    excluded_from_revision = Column(Boolean, nullable=False, server_default="true")
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "project_id", "metric_id",
            name="project_dataset_exclusions_project_metric_key",
        ),
    )
