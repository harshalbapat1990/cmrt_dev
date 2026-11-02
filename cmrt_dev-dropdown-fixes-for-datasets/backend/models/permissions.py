import uuid as _uuid
from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
