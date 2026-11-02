from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class JurisdictionBase(BaseModel):
    name: str = Field(max_length=255)
    code: Optional[str] = Field(default=None, max_length=10)
    type: Optional[str] = Field(default=None, max_length=50)  # 'country' or 'region'
    parent_id: Optional[UUID] = Field(default=None)  # Parent jurisdiction (e.g., country for regions)


class JurisdictionCreate(JurisdictionBase):
    pass


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    code: Optional[str] = Field(default=None, max_length=10)
    type: Optional[str] = Field(default=None, max_length=50)
    parent_id: Optional[UUID] = Field(default=None)


class JurisdictionOut(JurisdictionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
