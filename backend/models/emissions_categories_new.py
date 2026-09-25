import uuid as _uuid
from sqlalchemy import Column, String, SmallInteger, Integer, Boolean, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class EmissionsCategoryRecord(Base):
    __tablename__ = "emissions_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    code = Column(String, nullable=True)
    name = Column(String, nullable=False)
    scope = Column(SmallInteger, nullable=True)
    # NOTE: self-referential FK for parent category (enabling hierarchical categorisation). This is added post-table-creation via use_alter in the migration to avoid circular dependency issues.
    parent_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("emissions_categories.id", use_alter=True, name="fk__emissions_categories__parent_id"),
        nullable=True,
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    sort_order = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("emissions_categories_parent_category_id_idx", "parent_category_id"),
        Index("emissions_categories_scope_idx", "scope"),
    )
