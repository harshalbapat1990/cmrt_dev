from sqlalchemy import Column, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class FreightRailFactor(Base):
    __tablename__ = "freight_rail_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    train_type = Column(String(100), nullable=False)
    terrain = Column(String(50), nullable=False)
    fuel_consumption_l_per_000_gtk = Column(Numeric(10, 4), nullable=True)
    source_note = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_revision_id", "train_type", "terrain",
            name="uq_freight_rail_factors",
        ),
    )
