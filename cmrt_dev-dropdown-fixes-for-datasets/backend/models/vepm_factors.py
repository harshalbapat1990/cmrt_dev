from sqlalchemy import Column, ForeignKey, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class VepmFactor(Base):
    __tablename__ = "vepm_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year = Column(SmallInteger, nullable=False)
    speed_kmh = Column(SmallInteger, nullable=False)
    fleet_average_co2e_g_km = Column(Numeric(10, 4), nullable=True)
    light_vehicle_co2e_g_km = Column(Numeric(10, 4), nullable=True)
    heavy_vehicle_co2e_g_km = Column(Numeric(10, 4), nullable=True)
    bus_co2e_g_km = Column(Numeric(10, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_revision_id", "year", "speed_kmh",
            name="uq_vepm_factors",
        ),
    )
