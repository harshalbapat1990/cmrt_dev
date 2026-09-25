
# app/models/lookup.py
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.base import Base

class EmissionSource(Base):
    __tablename__ = "emission_source"
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(200), nullable=False)
    emissions_sub_category_id = Column(UUID(as_uuid=True))  # FK removed — emissions_sub_category table dropped
    measurement_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"))  # default display unit
    is_active = Column(Boolean, default=True)
    created_on = Column(TIMESTAMP)
    updated_on = Column(TIMESTAMP)

class EmissionFactor(Base):
    __tablename__ = "emission_factor"
    id = Column(UUID(as_uuid=True), primary_key=True)
    emission_source_id = Column(UUID(as_uuid=True), ForeignKey("emission_source.id"), nullable=False)
    measurement_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_on = Column(TIMESTAMP)
    updated_on = Column(TIMESTAMP)

class EmissionFactorValue(Base):
    __tablename__ = "emission_factor_value"
    id = Column(UUID(as_uuid=True), primary_key=True)
    emission_factor_id = Column(UUID(as_uuid=True), ForeignKey("emission_factor.id"), nullable=False)
    stage_code = Column(String(100), nullable=False)  # e.g., 'A1-3', 'A4', 'A5', ...
    gwp_kgco2e_per_unit = Column(Numeric(18, 6), nullable=False)
    created_on = Column(TIMESTAMP)
    updated_on = Column(TIMESTAMP)
