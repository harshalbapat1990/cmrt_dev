import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base

class OrganizationDomain(Base):
    __tablename__ = "organization_domains"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    domain = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        UniqueConstraint("organization_id", "domain", name="organization_domains_organization_id_domain_key"),
        Index("organization_domains_domain_idx", "domain"),
    )
