import uuid as _uuid
from sqlalchemy import Column, ForeignKey, Numeric, String, Text, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base


class EnergyDensityConversion(Base):
    __tablename__ = "energy_density_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    category = Column(String, nullable=False)  # 'Solid fuels', 'Gaseous fuels', 'Liquid fuels'
    name = Column(String, nullable=False)  # e.g., 'Dry wood', 'Natural gas'
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True)
    energy_density = Column(Numeric, nullable=False)  # Energy density value
    source_comments = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    dataset_revision = relationship("DatasetRevision", foreign_keys=[dataset_revision_id], lazy="selectin")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="selectin")

    __table_args__ = (
        Index(
            "uq_energy_density_global_key",
            "category", "name", "unit_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_energy_density_revision_key",
            "category", "name", "unit_id", "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
