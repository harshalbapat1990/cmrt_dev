from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.base import Base


class DirectSubstitutionFactor(Base):
    """BAU direct substitution equivalence rows (asphalt mixes, etc.) per jurisdiction."""

    __tablename__ = "direct_substitution_factors"

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
        nullable=False,
        index=True,
    )
    user_emissions_source = Column(Text, nullable=False)
    user_unit = Column(String(64), nullable=False)
    bau_equivalent_emission_source = Column(Text, nullable=False)
    bau_equivalent_unit = Column(String(64), nullable=False)
    bau_quantity_per_user_unit = Column(Numeric(24, 12), nullable=False)
    display_order = Column(Integer, nullable=False, server_default="0")

    jurisdiction = relationship("Jurisdiction", lazy="joined")

    __table_args__ = (Index("ix_direct_substitution_factors_jur_order", "jurisdiction_id", "display_order"),)
