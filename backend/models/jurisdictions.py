import uuid as _uuid
from sqlalchemy import Column, String, TIMESTAMP, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    type = Column(String, nullable=True)  # 'country' or 'region'
    parent_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)  # For hierarchical relationship (country-region)
    created_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("name", name="jurisdictions_name_key"),
    )
