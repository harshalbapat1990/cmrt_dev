import uuid as _uuid
from sqlalchemy import Column, String, Text, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from core.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)
    field_name = Column(String)
    old_value = Column(Text)
    new_value = Column(Text)
    performed_by = Column(UUID(as_uuid=True))
    performed_by_org = Column(UUID(as_uuid=True))
    performed_at = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    event_metadata = Column("metadata", JSONB)
    performed_by_email = Column(String(255), nullable=True)
    performed_by_org_name = Column(String(255), nullable=True)
    entity_name = Column(String(500), nullable=True)
    __table_args__ = (
        Index(
            "audit_logs_entity_type_entity_id_performed_at_idx",
            "entity_type",
            "entity_id",
            "performed_at",
        ),
    )
