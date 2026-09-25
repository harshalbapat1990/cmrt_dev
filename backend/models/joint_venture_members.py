import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, Numeric, Date, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base

class JointVentureMember(Base):
    __tablename__ = "joint_venture_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    joint_venture_id = Column(UUID(as_uuid=True), ForeignKey("joint_ventures.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    ownership_pct = Column(Numeric)
    role = Column(String)
    effective_from = Column(Date)
    effective_to = Column(Date)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        UniqueConstraint("joint_venture_id", "organization_id", name="joint_venture_members_joint_venture_id_organization_id_key"),
        Index("joint_venture_members_joint_venture_id_idx", "joint_venture_id"),
        Index("joint_venture_members_organization_id_idx", "organization_id"),
    )
