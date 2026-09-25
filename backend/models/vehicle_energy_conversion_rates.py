from sqlalchemy import Column, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class VehicleEnergyConversionRate(Base):
    __tablename__ = "vehicle_energy_conversion_rates"

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
    ev_projection_category = Column(String(100), nullable=False)
    primary_ice_fuel = Column(String(200), nullable=False)
    hybrid_fuel_savings_pct = Column(Numeric(6, 4), nullable=False)
    phev_fuel_savings_pct = Column(Numeric(6, 4), nullable=False)
    bev_energy_shift_kwh_per_l = Column(Numeric(10, 4), nullable=False)
    fcev_hydrogen_consumption_kwh_per_l = Column(Numeric(10, 4), nullable=False)
    source_comments = Column(Text, nullable=True)

    __table_args__ = (
        Index(
            "uq_vehicle_energy_conversion_rates_global",
            "vehicle_class_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_vehicle_energy_conversion_rates_revision",
            "vehicle_class_id",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("dataset_revision_id IS NOT NULL"),
        ),
    )
