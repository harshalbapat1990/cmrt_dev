import uuid as _uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base


PERIOD_STATUSES = (
    "in_progress",
    "awaiting_approval",
    "approved",
    "rejected",
    "reopen_requested",
)


class ProjectReportingSubmission(Base):
    __tablename__ = "project_reporting_submission"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    stage_instance_id = Column(UUID(as_uuid=True), ForeignKey("project_stage_instances.id", ondelete="CASCADE"), nullable=True)
    frequency = Column(String(50), nullable=False)
    period_label = Column(String(100), nullable=False)
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, server_default="in_progress")

    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(TIMESTAMP(timezone=False), nullable=True)

    decision_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision_at = Column(TIMESTAMP(timezone=False), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    reopen_requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reopen_requested_at = Column(TIMESTAMP(timezone=False), nullable=True)
    reopen_reason = Column(Text, nullable=True)
    exec_summary = Column(Text, nullable=True)
    exec_summary_author = Column(Text, nullable=True)
    exec_summary_date = Column(TIMESTAMP(timezone=False), nullable=True)

    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
