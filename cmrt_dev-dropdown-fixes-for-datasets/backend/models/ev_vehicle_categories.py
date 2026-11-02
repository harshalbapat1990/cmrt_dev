from sqlalchemy import Column, String

from core.base import Base


class EvVehicleCategory(Base):
    __tablename__ = "ev_vehicle_categories"

    code = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)
