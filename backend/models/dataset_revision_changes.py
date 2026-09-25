import uuid as _uuid
from sqlalchemy import Column, Numeric, String, Text, TIMESTAMP
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from core.base import Base


class DatasetRevisionChange(Base):
    __tablename__ = "dataset_revision_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    dataset_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id"),
        nullable=False,
    )
    metric_natural_key = Column(JSONB, nullable=False, server_default='{}')
    change_type = Column(String(50), nullable=False)
    old_value = Column(Numeric, nullable=True)
    new_value = Column(Numeric, nullable=True)
    reason = Column(Text, nullable=True)
    changed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
