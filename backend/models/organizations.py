import uuid as _uuid
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func, text
from core.base import Base

class Organization_Type(PyEnum):
    DESIGNERS = "DESIGNERS"
    CONTRACTORS = "CONTRACTORS"
    PLATFORM_OPERATOR = "PLATFORM_OPERATOR"   # Austroads / platform operator orgs

class Organization(Base):
    __tablename__ = "organization"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    organization_type = Column(
        "type",
        Enum(Organization_Type, name="organization_type", create_type=False),
        nullable=False,
    )  # DESIGNERS / CONTRACTORS / PLATFORM_OPERATOR
    type = synonym("organization_type")
    country = Column(String)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    region_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    
    is_proponent = Column(Boolean, nullable=False, server_default=text("true"), default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    
    # Relationships
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id], lazy="selectin")
    region = relationship("Jurisdiction", foreign_keys=[region_id], lazy="selectin")

    @property
    def jurisdiction_name(self) -> str | None:
        return self.jurisdiction.name if self.jurisdiction else None

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None