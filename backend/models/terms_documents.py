import uuid as _uuid
import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from core.base import Base


class TermsDocumentType(str, enum.Enum):
    PICS = "PICS"                  # Personal Information Collection Statement
    TERMS_OF_USE = "TERMS_OF_USE"  # CMRT Terms of Use


class TermsDocument(Base):
    __tablename__ = "terms_documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    document_type = Column(Enum(TermsDocumentType, name="terms_document_type"), nullable=False)
    version = Column(Integer, nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_backend = Column(String(32), nullable=False, server_default="db")
    # Interim: raw PDF bytes (NULL when using Azure Blob)
    file_data = Column(LargeBinary, nullable=True)
    # Future: Azure Blob Storage path (NULL until blob is connected)
    storage_key = Column(Text, nullable=True)
    uploaded_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="false")

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id], lazy="selectin")
