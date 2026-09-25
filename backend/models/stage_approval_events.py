import uuid as _uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


STAGE_EVENT_TYPES = (
    "submitted",
    "approved",
    "rejected",
    "reopen_requested",
    "reopen_approved",
    "reopen_rejected",
)


class StageApprovalEvent(Base):
    __tablename__ = "stage_approval_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    stage_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(30), nullable=False)
    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_at = Column(
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    justification = Column(Text, nullable=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    report_number = Column(Integer, nullable=True)
    submission_period_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_reporting_submission.id", ondelete="CASCADE"),
        nullable=True,
    )
