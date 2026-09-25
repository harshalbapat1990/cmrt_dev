from sqlalchemy import Boolean, Column, String
from core.base import Base


class DecarbFactorType(Base):
    __tablename__ = "decarb_factor_types"

    code = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)
    has_region = Column(Boolean, nullable=False, default=False)
    unit = Column(String(20), nullable=False)
