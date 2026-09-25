import uuid as _uuid
from sqlalchemy import Column, ForeignKey, TIMESTAMP, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from enum import Enum as PyEnum
from core.base import Base

class OrgRole(PyEnum):
    PROPONENT = "PROPONENT"
    DESIGNER = "DESIGNER"
    DELIVERY = "DELIVERY"

class ProjectOrganization(Base):
    __tablename__ = "project_organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    role = Column(Enum(OrgRole, name="org_role", create_type=False), nullable=False)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)