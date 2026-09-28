import uuid as _uuid
from sqlalchemy import Boolean, Column, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.base import Base


class ProjectDatasetRevision(Base):
    __tablename__ = "project_dataset_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id"),
        nullable=False,
    )
    applied_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    is_locked = Column(Boolean, nullable=False, server_default="false")
    notes = Column(Text, nullable=True)
    calculation_report = Column(JSONB, nullable=False, server_default="{}")

    revision = relationship("DatasetRevision", lazy="selectin", foreign_keys=[dataset_revision_id])

    __table_args__ = (
        UniqueConstraint(
            "project_id", "dataset_revision_id",
            name="project_dataset_revisions_project_revision_key",
        ),
    )
