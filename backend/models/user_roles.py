import uuid as _uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    scope_type = Column(String)
    scope_id = Column(UUID(as_uuid=True))
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="user_roles_user_id_role_id_scope_type_scope_id_key"),
    )
