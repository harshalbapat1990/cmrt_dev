import uuid as _uuid
from sqlalchemy import Boolean, Column, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class EmissionsFactorSet(Base):
    __tablename__ = "emissions_factor_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    is_locked = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
