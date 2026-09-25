from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class BaseCaseAssumption(Base):
    __tablename__ = "base_case_assumptions"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String, nullable=False)
    emissions_category_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=False)
    default_value = Column(Numeric, nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    is_anz_default = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("emissions_category_id", "name", name="base_case_assumptions_category_name_key"),
    )
