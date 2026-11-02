import uuid as _uuid
from sqlalchemy import Column, ForeignKey, Numeric, String, Text, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base


class Fugitive(Base):
    __tablename__ = "fugitives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True)
    equipment_type = Column(String, nullable=False)
    default_annual_leakage_rate = Column(Numeric, nullable=False)  # Stored as decimal (e.g., 9.00)
    source_comments = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    dataset_revision = relationship("DatasetRevision", foreign_keys=[dataset_revision_id], lazy="selectin")
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id], lazy="selectin")

    __table_args__ = (
        Index(
            "uq_fugitives_global_key",
            "jurisdiction_id", "equipment_type",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_fugitives_revision_key",
            "jurisdiction_id", "equipment_type", "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
