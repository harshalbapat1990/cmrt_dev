from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class VehicleClass(Base):
    __tablename__ = "vehicle_classes"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("name", name="uq_vehicle_classes_name"),
    )
