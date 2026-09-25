from sqlalchemy import Column, ForeignKey, Index, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class UninterruptedVehicle(Base):
    __tablename__ = "uninterrupted_vehicles"

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
    gradient_m_per_km = Column(Numeric(10, 2), nullable=False, server_default=text("0"))
    curvature_deg_per_km = Column(Numeric(10, 2), nullable=False)
    base_fuel_l_per_100km = Column(Numeric(10, 4), nullable=False)
    k1 = Column(Numeric(10, 4), nullable=False)
    k2 = Column(Numeric(10, 4), nullable=False)
    k3 = Column(Numeric(10, 4), nullable=False)
    k4 = Column(Numeric(10, 4), nullable=False)
    k5 = Column(Numeric(10, 4), nullable=False)

    __table_args__ = (
        Index(
            "uq_uninterrupted_vehicles_global",
            "vehicle_class_id",
            "gradient_m_per_km",
            "curvature_deg_per_km",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_uninterrupted_vehicles_revision",
            "vehicle_class_id",
            "gradient_m_per_km",
            "curvature_deg_per_km",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
