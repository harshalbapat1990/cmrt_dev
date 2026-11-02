import uuid as _uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class JurisdictionReportingStage(Base):
    __tablename__ = "jurisdiction_reporting_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    anz_reporting_stage_id = Column(UUID(as_uuid=True), ForeignKey("anz_reporting_stages.id"), nullable=False)
    name = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "name", name="jurisdiction_reporting_stages_jurisdiction_id_name_key"),
        Index("jurisdiction_reporting_stages_jurisdiction_id_idx", "jurisdiction_id"),
        Index("jurisdiction_reporting_stages_anz_stage_id_idx", "anz_reporting_stage_id"),
    )
