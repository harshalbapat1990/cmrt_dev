from sqlalchemy import Column, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class CarbonValue(Base):
    __tablename__ = "carbon_values"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    range_code = Column(String(50), ForeignKey("carbon_value_ranges.code"), nullable=False)
    year = Column(SmallInteger, nullable=False)
    value = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=True)
    source = Column(String(500), nullable=True)

    __table_args__ = (
        Index(
            "uq_carbon_value",
            "dataset_revision_id", "jurisdiction_id", "range_code", "year",
            unique=True,
        ),
    )
