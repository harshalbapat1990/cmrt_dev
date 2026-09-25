import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from sqlalchemy.sql import func, text
from core.base import Base

class EmissionEntry(Base):
    __tablename__ = "emission_entry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    project_reporting_submission_id = Column(UUID(as_uuid=True), ForeignKey("project_reporting_submission.id"), nullable=False)
    emissions_sub_category_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=False)
    emission_source_id = Column(UUID(as_uuid=True), ForeignKey("emission_source.id"), nullable=False)
    measurement_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    emission_factor_id = Column(UUID(as_uuid=True), ForeignKey("emission_factor.id"), nullable=False)

    data_quality = Column(String(50), nullable=False)
    quantity = Column(NUMERIC(18, 6), nullable=False)
    notes = Column(String(100), nullable=True)
    emissions_tco2e = Column(NUMERIC(18, 6), nullable=False)

    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)

class EmissionEntrySummary(Base):
    __tablename__ = "emission_entry_summary"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "project_reporting_submission_id",
            name="emission_entry_summary_project_id_project_reporting_submiss_key",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    project_reporting_submission_id = Column(UUID(as_uuid=True), ForeignKey("project_reporting_submission.id"), nullable=False)

    summary = Column(String(1000), nullable=True)

    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
