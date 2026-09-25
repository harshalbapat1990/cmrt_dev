from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EmissionsFactorSetCreate(BaseModel):
    name: str = Field(max_length=255)
    version: str = Field(max_length=100)
    dataset_revision_id: Optional[UUID] = None
    notes: Optional[str] = None


class EmissionsFactorSetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    version: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None


class EmissionsFactorSetDuplicate(BaseModel):
    new_version: str = Field(max_length=100)
    name: Optional[str] = Field(default=None, max_length=255)


class EmissionsFactorSetOut(BaseModel):
    id: UUID
    name: str
    version: str
    dataset_revision_id: Optional[UUID] = None
    notes: Optional[str] = None
    is_locked: bool
    created_at: datetime

    class Config:
        from_attributes = True
