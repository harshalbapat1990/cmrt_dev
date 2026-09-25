import uuid as _uuid

from sqlalchemy import Column, ForeignKey, Index, Numeric, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from core.base import Base


class ActivityData(Base):
    __tablename__ = "activity_data"

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

    component_id = Column(UUID(as_uuid=True), nullable=True)

    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric_natural_key = Column(JSONB, nullable=True)

    quantity = Column(Numeric, nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id", ondelete="RESTRICT"), nullable=True)

    ui_table_key = Column(String(64), nullable=False)

    lifecycle_module_code = Column(String, ForeignKey("lifecycle_modules.code"), nullable=True)

    extra_fields = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=False), nullable=True, onupdate=func.now())

    submission_period_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_reporting_submission.id", ondelete="SET NULL"),
        nullable=True,
    )

    project_mitigation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_mitigations.id", ondelete="CASCADE"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_activity_data_stage_table", "project_stage_instance_id", "ui_table_key"),
        Index("ix_activity_data_project_id", "project_id"),
        Index("ix_activity_data_period_id", "submission_period_id"),
    )