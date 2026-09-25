import uuid as _uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from core.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"))
    email = Column(String, nullable=False, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True)
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_on = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)
    oidc_sub = Column(String)
    oidc_issuer = Column(String)
    # Acceptance is tied to the terms_documents.version active when the user registered.
    pics_accepted = Column(Boolean, nullable=False, default=False, server_default="false")
    pics_accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    pics_version = Column(Integer, nullable=True)
    terms_accepted = Column(Boolean, nullable=False, default=False, server_default="false")
    terms_accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    terms_version = Column(Integer, nullable=True)
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        UniqueConstraint("username", name="users_username_key"),
    )
