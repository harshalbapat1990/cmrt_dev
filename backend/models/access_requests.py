import uuid as _uuid
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from core.base import Base


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))

    request_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, server_default="PENDING")
    requester_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    requested_role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    scope_type = Column(String(20), nullable=False, server_default="GLOBAL")
    scope_id   = Column(UUID(as_uuid=True), nullable=True)
    organisation_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=True)
    project_id      = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=True)
    reason = Column(Text, nullable=True)
    decision_note      = Column(Text, nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at        = Column(TIMESTAMP(timezone=False), nullable=True)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    event_metadata = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_access_requests_status",
        ),
        CheckConstraint(
            "scope_type IN ('GLOBAL', 'ORGANISATION', 'PROJECT', 'STAGE')",
            name="ck_access_requests_scope_type",
        ),
        Index("ix_access_requests_status", "status"),
        Index("ix_access_requests_organisation_id", "organisation_id"),
        Index("ix_access_requests_target_user_id", "target_user_id"),
    )
