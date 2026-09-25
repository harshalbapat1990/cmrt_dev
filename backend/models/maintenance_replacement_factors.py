from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.base import Base


class MaintenanceReplacementFactor(Base):
    __tablename__ = "maintenance_replacement_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    activity_type = Column(String(100), nullable=False)
    item = Column(String(255), nullable=False)
    unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    unit = relationship("Unit", lazy="joined")
    product_emissions_tco2e = Column(Numeric(12, 6), nullable=True)
    transport_emissions_tco2e = Column(Numeric(12, 6), nullable=True)
    installation_emissions_tco2e = Column(Numeric(12, 6), nullable=True)
    emissions_intensity_tco2e = Column(Numeric(12, 6), nullable=True)
    default_frequency_years = Column(Integer, nullable=True)
    source_note = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dataset_revision_id", "jurisdiction_id", "activity_type", "item",
            name="uq_maintenance_replacement_factors",
        ),
    )
