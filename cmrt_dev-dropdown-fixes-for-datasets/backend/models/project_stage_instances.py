import uuid as _uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.base import Base


class ProjectStage(PyEnum):
    BUSINESS_CASE = "BUSINESS_CASE"
    DESIGN = "DESIGN"
    CONSTRUCTION = "CONSTRUCTION"
    RECURRING = "RECURRING"


APPROVAL_STATUSES = ("draft", "submitted", "in_review", "tech_approved", "final_approved")

STAGE_SEQUENCE: dict[str, int] = {
    "BUSINESS_CASE": 1,
    "DESIGN": 2,
    "CONSTRUCTION": 3,
}


class ProjectStageInstance(Base):
    __tablename__ = "project_stage_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    stage = Column(Enum(ProjectStage, name="project_stage", create_type=False), nullable=False)

    sequence = Column(Integer, nullable=False, default=0)

    num_reports_required = Column(Integer, nullable=True)
    frequency = Column(String(20), nullable=True)

    approval_status = Column(String(20), nullable=False, server_default="draft", default="draft")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(TIMESTAMP(timezone=False), nullable=True)          # final approval timestamp
    technical_approved_at = Column(TIMESTAMP(timezone=False), nullable=True) # tech approval timestamp

    submitted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at = Column(TIMESTAMP(timezone=False), nullable=True)
    current_justification = Column(String, nullable=True)

    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)

    project = relationship("Project", foreign_keys=[project_id], lazy="noload", overlaps="stage_instances")

    @property
    def project_name(self):
        return self.project.project_name if self.project is not None else None

    __table_args__ = (
        UniqueConstraint("project_id", "stage", name="project_stage_instances_project_id_stage_key"),
    )
