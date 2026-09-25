import uuid as _uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class ProjectOption(Base):
    __tablename__ = "project_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    stage_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_stage_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_number = Column(Integer, nullable=False, default=1)
    option_number = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    approval_status = Column(String(30), nullable=False, server_default="draft", default="draft")
    current_justification = Column(Text, nullable=True)
    exec_summary = Column(Text, nullable=True)
    exec_summary_author = Column(Text, nullable=True)
    exec_summary_date = Column(TIMESTAMP(timezone=False), nullable=True)

    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "project_id", "stage_instance_id", "report_number", "option_number",
            name="project_options_project_stage_report_option_key",
        ),
    )
