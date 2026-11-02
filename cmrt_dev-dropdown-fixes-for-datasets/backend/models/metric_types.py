import uuid as _uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class MetricType(Base):
    __tablename__ = "metric_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("code", name="metric_types_code_key"),
    )
