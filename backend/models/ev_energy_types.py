from sqlalchemy import Column, String

from core.base import Base


class EvEnergyType(Base):
    __tablename__ = "ev_energy_types"

    code = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(50), nullable=False)
