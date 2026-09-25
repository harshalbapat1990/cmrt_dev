import uuid as _uuid
from sqlalchemy import Column, String, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from sqlalchemy.sql import func, text

from core.base import Base


class ConcreteMixProduction(Base):
    """
    Global reference table for production-stage (A3) emission factors per m3 of concrete.

    Each row represents one energy/waste item from AusLCI Concrete Unit Processes
    (e.g. Diesel, Electricity, Wastewater treatment).

    Production Stage EF (tCO2e/m3) = SUM(emissions_kgco2e_m3) / 1000 across all active rows.
    This value is fixed and locked from user access — it does not vary per mix design.
    """

    __tablename__ = "concrete_mix_production"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    emissions_source = Column(String(300), nullable=False)
    use_per_m3 = Column(NUMERIC(14, 6), nullable=False)
    units = Column(String(20), nullable=False)
    ef_kgco2e_per_unit = Column(NUMERIC(14, 8), nullable=False)
    # Computed at seed time: use_per_m3 × ef_kgco2e_per_unit
    emissions_kgco2e_m3 = Column(NUMERIC(14, 8), nullable=False)
    use_source = Column(Text(), nullable=True)
    ef_source = Column(Text(), nullable=True)
    is_active = Column(Boolean(), nullable=False, server_default=text("TRUE"))
    sort_order = Column(Integer(), nullable=False, server_default=text("0"))

    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now(), nullable=True)
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
