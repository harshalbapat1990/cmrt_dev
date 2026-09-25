import uuid as _uuid
from sqlalchemy import Boolean, Column, Date, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base

# Lifecycle statuses for a Dataset Revisioning system
# draft      → editable, not yet usable for project binding
# published  → active; projects may bind to this revision
# deprecated → superseded by a newer revision but existing bindings intact
# archived   → retired; no new bindings or edits allowed
REVISION_STATUSES = ("draft", "published", "deprecated", "archived")

# Dataset scope tiers
# DEFAULT  → platform-global revisions (managed by SUPER_ADMIN)
# ORG      → organisation-scoped revisions (managed by ORG_ADMIN, scope_id = org UUID)
# PROJECT  → project-scoped revisions (managed by PROJECT_ADMIN/EDITOR, scope_id = project UUID)
REVISION_SCOPE_TYPES = ("DEFAULT", "ORG", "PROJECT")


class DatasetRevision(Base):
    __tablename__ = "dataset_revisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    status = Column(String(20), nullable=False, server_default="draft", default="draft")
    scope_type = Column(String(20), nullable=False, server_default="DEFAULT", default="DEFAULT")
    scope_id = Column(UUID(as_uuid=True), nullable=True)
    applicable_from = Column(Date, nullable=True)
    applicable_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    parent_revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dataset_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("name", "scope_type", "scope_id", name="dataset_revisions_name_scope_key"),
    )
