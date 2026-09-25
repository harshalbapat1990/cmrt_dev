import uuid as _uuid
from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base


class Unit(Base):
    __tablename__ = "units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    code = Column(String, nullable=False)
    label = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("code", name="units_code_key"),
    )
