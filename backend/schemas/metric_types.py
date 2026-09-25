from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class MetricTypeBase(BaseModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: Optional[str] = None


class MetricTypeCreate(MetricTypeBase):
    pass


class MetricTypeUpdate(BaseModel):
    code: Optional[str] = Field(default=None, max_length=100)
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class MetricTypeOut(MetricTypeBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
