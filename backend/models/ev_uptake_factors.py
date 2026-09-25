from sqlalchemy import Column, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class EvUptakeFactor(Base):
    __tablename__ = "ev_uptake_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    scenario_code = Column(String(50), ForeignKey("ev_scenario_types.code"), nullable=False)
    vehicle_category_code = Column(String(50), ForeignKey("ev_vehicle_categories.code"), nullable=False)
    energy_type_code = Column(String(50), ForeignKey("ev_energy_types.code"), nullable=False)
    year = Column(SmallInteger, nullable=False)
    uptake_pct = Column(Numeric(7, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_revision_id", "jurisdiction_id", "scenario_code",
            "vehicle_category_code", "energy_type_code", "year",
            name="uq_ev_uptake_factors",
        ),
    )
