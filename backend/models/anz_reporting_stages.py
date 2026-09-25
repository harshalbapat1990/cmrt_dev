import uuid as _uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class AnzReportingStage(Base):
    __tablename__ = "anz_reporting_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", name="anz_reporting_stages_name_key"),
    )
