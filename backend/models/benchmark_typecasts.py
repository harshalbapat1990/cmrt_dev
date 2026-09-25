import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class BenchmarkTypecast(Base):
    __tablename__ = "benchmark_typecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    mastertype_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_mastertypes.id"), nullable=False)

    __table_args__ = (UniqueConstraint("name", "mastertype_id", name="uq_benchmark_typecasts_name_mastertype"),)
