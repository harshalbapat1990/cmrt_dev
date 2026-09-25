from sqlalchemy import Column, ForeignKey, Index, Numeric, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class DefaultWastageRate(Base):
    __tablename__ = "default_wastage_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())

    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True)

    # Wastage rates as percentages
    construction_wastage_rate = Column(Numeric, nullable=False)  # e.g., 5.00
    recycling_rate = Column(Numeric, nullable=False)  # e.g., 90.00
    landfill_rate = Column(Numeric, nullable=False)  # e.g., 10.00

    source = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id], lazy="selectin")
    material = relationship("Material", foreign_keys=[material_id], lazy="selectin")
    dataset_revision = relationship("DatasetRevision", foreign_keys=[dataset_revision_id], lazy="selectin")

    __table_args__ = (
        Index(
            "uq_wastage_rates_global_key",
            "jurisdiction_id", "material_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_wastage_rates_revision_key",
            "jurisdiction_id", "material_id", "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
