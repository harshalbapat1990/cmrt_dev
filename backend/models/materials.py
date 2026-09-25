from sqlalchemy import Boolean, Column, ForeignKey, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    emissions_category_id = Column(UUID(as_uuid=True), ForeignKey("emissions_categories.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", name="materials_name_key"),
    )
