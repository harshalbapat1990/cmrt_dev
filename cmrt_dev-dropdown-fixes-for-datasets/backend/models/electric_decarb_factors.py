from sqlalchemy import Column, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class ElectricDecarbFactor(Base):
    __tablename__ = "electric_decarb_factors"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    factor_type_code = Column(String(50), ForeignKey("decarb_factor_types.code"), nullable=False)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("grid_regions.id"), nullable=True)
    unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    year = Column(SmallInteger, nullable=False)
    value = Column(Numeric(10, 6), nullable=True)
    value_qualifier = Column(String(5), nullable=True)

    __table_args__ = (
        Index(
            "uq_edf_no_region",
            "dataset_revision_id", "factor_type_code", "jurisdiction_id", "year",
            unique=True,
            postgresql_where=text("region_id IS NULL"),
        ),
        Index(
            "uq_edf_with_region",
            "dataset_revision_id", "factor_type_code", "region_id", "year",
            unique=True,
            postgresql_where=text("region_id IS NOT NULL"),
        ),
    )
