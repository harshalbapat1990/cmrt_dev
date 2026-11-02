import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base

class ProjectParty(Base):
    __tablename__ = "project_parties"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"))
    joint_venture_id = Column(UUID(as_uuid=True), ForeignKey("joint_ventures.id"))
    role = Column(String, nullable=False)
    role_note = Column(String)
    contract_number = Column(String)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        Index("project_parties_project_id_idx", "project_id"),
        Index("project_parties_organization_id_idx", "organization_id"),
        Index("project_parties_joint_venture_id_idx", "joint_venture_id"),
        Index("project_parties_project_id_organization_id_role_idx", "project_id", "organization_id", "role"),
        Index("project_parties_project_id_joint_venture_id_role_idx", "project_id", "joint_venture_id", "role"),
    )
