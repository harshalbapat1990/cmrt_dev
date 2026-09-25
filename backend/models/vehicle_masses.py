from sqlalchemy import Column, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class VehicleMass(Base):
    __tablename__ = "vehicle_masses"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    vehicle_class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_classes.id", ondelete="CASCADE"),
        nullable=False,
    )
    reference_gcm_tonnes = Column(Numeric(10, 4), nullable=True)
    max_payload_tonnes = Column(Numeric(10, 4), nullable=False)
    gvm_tonnes = Column(Numeric(10, 4), nullable=False)
    assumed_payload_pct = Column(Numeric(5, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("vehicle_class_id", name="uq_vehicle_masses_vehicle_class_id"),
    )
