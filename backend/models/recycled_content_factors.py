from sqlalchemy import Boolean, Column, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from core.base import Base


class RecycledContentFactor(Base):
    __tablename__ = "recycled_content_factors"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=func.gen_random_uuid(),
    )
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    jurisdiction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jurisdictions.id"),
        nullable=True,
        index=True,
    )
    emissions_sub_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("emissions_categories.id"),
        nullable=True,
        index=True,
    )
    emissions_source = Column(String, nullable=False, index=True)
    recycled_content_pct = Column(Numeric, nullable=True)
    reused_content_pct = Column(Numeric, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)

    __table_args__ = (
        Index(
            "uq_rcf_global_jurisdiction_source",
            "jurisdiction_id",
            "emissions_source",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NULL"),
        ),
        Index(
            "uq_rcf_revision_jurisdiction_source",
            "jurisdiction_id",
            "emissions_source",
            "dataset_revision_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND dataset_revision_id IS NOT NULL"),
        ),
    )
