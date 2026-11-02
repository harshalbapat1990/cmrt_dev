from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserGuideVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    filename: str
    file_size: int
    storage_backend: str
    uploaded_by_id: Optional[UUID] = None
    uploaded_at: datetime
    is_active: bool


class UserGuideUploadResponse(UserGuideVersionOut):
    pass
