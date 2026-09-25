from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class GridRegion(Base):
    __tablename__ = "grid_regions"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "name", name="uq_grid_regions_jur_name"),
    )
