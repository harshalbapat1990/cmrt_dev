import uuid as _uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base

class ProjectType(Base):
    __tablename__ = "project_type"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)

class ProjectTypecast(Base):
    __tablename__ = "project_typecast"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_type_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    is_maintenance = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
