from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from models.terms_documents import TermsDocumentType


class TermsDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type: TermsDocumentType
    version: int
    filename: str
    file_size: int
    storage_backend: str
    uploaded_by_id: Optional[UUID] = None
    uploaded_at: datetime
    is_active: bool


class TermsDocumentUploadResponse(TermsDocumentOut):
    pass
