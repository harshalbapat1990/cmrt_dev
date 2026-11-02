from sqlalchemy import Column, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class ProponentAssumptionOverride(Base):
    __tablename__ = "proponent_assumption_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    proponent_org_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    assumption_id = Column(UUID(as_uuid=True), ForeignKey("base_case_assumptions.id"), nullable=False)
    value = Column(Numeric, nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "proponent_org_id", "assumption_id", "effective_from",
            name="proponent_assumption_overrides_composite_key",
        ),
    )
