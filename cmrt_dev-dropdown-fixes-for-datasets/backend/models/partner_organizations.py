import uuid as _uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.base import Base


class PartnerOrganization(Base):
    """A delivery partner directory entry, independent of registered organizations."""

    __tablename__ = "partner_organizations"
    __table_args__ = (
        CheckConstraint("partner_type IN ('DESIGNERS', 'CONTRACTORS')", name="ck_partner_organizations_type"),
        UniqueConstraint(
            "partner_type", "normalized_name",
            name="uq_partner_organizations_type_normalized_name",
        ),
        Index("ix_partner_organizations_type_active_name", "partner_type", "is_active", "name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    partner_type = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"), default=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())


class PartnerOrganizationSuggestion(Base):
    __tablename__ = "partner_organization_suggestions"
    __table_args__ = (
        Index(
            "uq_partner_org_suggestion_pending_name",
            "partner_type", "normalized_name", unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        CheckConstraint("partner_type IN ('DESIGNERS', 'CONTRACTORS')", name="ck_partner_org_suggestions_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_partner_org_suggestions_status"),
        Index("ix_partner_org_suggestions_status_created", "status", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    partner_type = Column(String(20), nullable=False)
    status = Column(String(12), nullable=False, server_default="pending", default="pending")
    submitted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    partner_organization_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.id"), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    reviewed_at = Column(DateTime(timezone=False), nullable=True)

    partner_organization = relationship("PartnerOrganization")


class ProjectPartnerOrganization(Base):
    __tablename__ = "project_partner_organizations"
    __table_args__ = (
        CheckConstraint(
            "(partner_organization_id IS NOT NULL AND custom_partner_name IS NULL) OR "
            "(partner_organization_id IS NULL AND custom_partner_name IS NOT NULL)",
            name="ck_project_partner_organizations_exactly_one_source",
        ),
        Index("ix_project_partner_organizations_project", "project_id"),
        Index("ix_project_partner_organizations_partner", "partner_organization_id"),
        CheckConstraint("role IN ('DESIGNER', 'DELIVERY')", name="ck_project_partner_organizations_role"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    partner_organization_id = Column(UUID(as_uuid=True), ForeignKey("partner_organizations.id"), nullable=True)
    custom_partner_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())

    partner_organization = relationship("PartnerOrganization")

    @property
    def partner_name(self) -> str | None:
        if self.partner_organization is not None:
            return self.partner_organization.name
        return self.custom_partner_name
