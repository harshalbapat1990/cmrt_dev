import uuid as _uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        UniqueConstraint("name", name="roles_name_key"),
    )
