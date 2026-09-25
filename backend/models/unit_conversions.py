import uuid as _uuid
from sqlalchemy import Column, ForeignKey, Index, Numeric, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class UnitConversion(Base):
    __tablename__ = "unit_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    from_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    to_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    factor = Column(Numeric, nullable=False)

    # Relationships
    dataset_revision = relationship("DatasetRevision", foreign_keys=[dataset_revision_id], lazy="selectin")
    from_unit = relationship("Unit", foreign_keys=[from_unit_id], lazy="selectin")
    to_unit = relationship("Unit", foreign_keys=[to_unit_id], lazy="selectin")

    __table_args__ = (
        Index(
            "uq_unit_conversions_global",
            "from_unit_id",
            "to_unit_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_unit_conversions_revision",
            "from_unit_id",
            "to_unit_id",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
        Index("unit_conversions_from_unit_idx", "from_unit_id"),
        Index("unit_conversions_to_unit_idx", "to_unit_id"),
    )
