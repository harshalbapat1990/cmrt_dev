from sqlalchemy import Column, ForeignKey, Index, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class InterruptedVehicle(Base):
    __tablename__ = "interrupted_vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    vehicle_class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
        nullable=False,
    )
    coefficient_a = Column(Numeric(12, 6), nullable=False)
    coefficient_b = Column(Numeric(12, 6), nullable=False)

    __table_args__ = (
        Index(
            "uq_interrupted_vehicles_global",
            "vehicle_class_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_interrupted_vehicles_revision",
            "vehicle_class_id",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
