from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class DefaultWasteRate(Base):
    __tablename__ = "default_waste_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    waste_treatment_id = Column(UUID(as_uuid=True), ForeignKey("waste_treatments.id"), nullable=False)
    applicable_lifecycle_module_code = Column(String, ForeignKey("lifecycle_modules.code"), nullable=True)
    basis = Column(String, nullable=False)
    rate = Column(Numeric, nullable=False)
    rate_unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    notes = Column(Text, nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    __table_args__ = (
        Index(
            "uq_dwr_global_composite",
            "jurisdiction_id", "material_id", "waste_treatment_id",
            "applicable_lifecycle_module_code", "basis",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_dwr_revision_composite",
            "jurisdiction_id", "material_id", "waste_treatment_id",
            "applicable_lifecycle_module_code", "basis", "dataset_revision_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NOT NULL"),
        ),
    )
