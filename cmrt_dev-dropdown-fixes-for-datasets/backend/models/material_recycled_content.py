from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class MaterialRecycledContent(Base):
    __tablename__ = "material_recycled_content"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    recycled_from_material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    percent = Column(Numeric, nullable=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    __table_args__ = (
        Index(
            "uq_mrc_global_jurisdiction_material",
            "jurisdiction_id", "material_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_mrc_revision_jurisdiction_material",
            "jurisdiction_id", "material_id", "dataset_revision_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NOT NULL"),
        ),
    )
