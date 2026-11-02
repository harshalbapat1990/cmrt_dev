from sqlalchemy import Column, Numeric, String
from core.base import Base

class Grade2ComponentLevel(Base):
    __tablename__ = "v_grade2_component_level"
    __table_args__ = {"extend_existing": True}

    jurisdiction = Column("Jurisdiction", String, primary_key=True)
    emissions_category = Column("Emissions Category", String, primary_key=True)
    emissions_sub_category = Column("Emissions Sub-Category", String, primary_key=True)
    emissions_source = Column("Emissions Source", String, primary_key=True)
    uom = Column("UoM", String, nullable=True)
    factor_a1_a3 = Column("Product Stage (A1-3) (tCO2e/UoM)", Numeric, nullable=True)
    factor_a4 = Column("Transport Stage (A4) (tCO2e/UoM)", Numeric, nullable=True)
    factor_a5 = Column("Construction Stage (A5) (tCO2e/UoM)", Numeric, nullable=True)
    source_comments = Column("Source/Comments", String, nullable=True)
