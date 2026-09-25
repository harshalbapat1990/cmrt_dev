import uuid as _uuid
from sqlalchemy import Column, ForeignKey, Integer, Boolean, TIMESTAMP, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from enum import Enum as PyEnum
from core.base import Base

class ProjectStage(PyEnum):
    BUSINESS_CASE = "BUSINESS_CASE"
    DESIGN = "DESIGN"
    CONSTRUCTION = "CONSTRUCTION"

class ReportFrequency(PyEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BI_MONTHLY = "BI_MONTHLY"
    ANNUAL = "ANNUAL"

class ProjectStageConfig(Base):
    __tablename__ = "project_stage_config"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    stage = Column(Enum(ProjectStage, name="project_stage", create_type=False), nullable=False)
    enabled = Column(Boolean, default=False)
    num_reports_required = Column(Integer, nullable=True)
    frequency = Column(Enum(ReportFrequency, name="report_frequency", create_type=False), nullable=True)
    min_requirements = Column(JSONB, nullable=True)

    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)