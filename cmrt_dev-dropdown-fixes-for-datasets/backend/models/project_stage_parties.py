import uuid as _uuid
from sqlalchemy import Column, ForeignKey, Boolean, TIMESTAMP, UniqueConstraint, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.base import Base

class ProjectStageParty(Base):
    __tablename__ = "project_stage_parties"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    project_stage_instance_id = Column(UUID(as_uuid=True), ForeignKey("project_stage_instances.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"))
    joint_venture_id = Column(UUID(as_uuid=True), ForeignKey("joint_ventures.id"))
    role = Column(String, nullable=False)
    role_note = Column(String)
    contract_number = Column(String)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "project_stage_instance_id",
            "joint_venture_id",
            "role",
            name="uq_psp_stageinst_jv_role",
        ),

        UniqueConstraint(
            "project_stage_instance_id",
            "organization_id",
            "role",
            name="uq_psp_stageinst_org_role",
        ),

        Index("ix_psp_stageinst", "project_stage_instance_id"),
        Index("ix_psp_org", "organization_id"),
        Index("ix_psp_jv", "joint_venture_id"),
    )
