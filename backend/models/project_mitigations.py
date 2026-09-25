import uuid as _uuid

from sqlalchemy import Column, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class ProjectMitigation(Base):
    """Per-option mitigation scenarios for large-project data entry (metadata + FK target for activity_data)."""

    __tablename__ = "project_mitigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    project_stage_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_option_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_options.id", ondelete="SET NULL"),
        nullable=True,
    )

    submission_stage = Column(String(32), nullable=False)
    name = Column(String(512), nullable=False)
    mitigation_type = Column(String(32), nullable=False)
    lifecycle_phase = Column(String(64), nullable=False)
    lifecycle_phase_label = Column(String(128), nullable=False)
    notes = Column(Text, nullable=True)
    group_label = Column(String(512), nullable=True)

    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=False), nullable=True, onupdate=func.now())