import uuid as _uuid

from sqlalchemy import Column, String, TIMESTAMP, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from enum import Enum as PyEnum
from core.base import Base

class AreaClass(PyEnum):
    METROPOLITAN = "METROPOLITAN"
    REGIONAL = "REGIONAL"
    REMOTE = "REMOTE"
    RURAL = "RURAL"

class PostcodeReference(Base):
    __tablename__ = "postcode_reference"
    __table_args__ = (UniqueConstraint("postcode", "jurisdiction_id", name="uq_postcode_jurisdiction"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    postcode = Column(String(10), nullable=False)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=True)
    area_class = Column(Enum(AreaClass, name="area_class", create_type=False), nullable=False)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    
    # Relationship
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])
    
class ProjectPostcode(Base):
    __tablename__ = "project_postcode"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=True)
    postcode = Column(String(10), nullable=False)
    area_class = Column(Enum(AreaClass, name="area_class", create_type=False), nullable=False)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    
    # Relationships
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])