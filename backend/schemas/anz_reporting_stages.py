from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AnzReportingStageBase(BaseModel):
    name: str = Field(max_length=255)
    sequence: int


class AnzReportingStageCreate(AnzReportingStageBase):
    pass


class AnzReportingStageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    sequence: Optional[int] = None


class AnzReportingStageOut(AnzReportingStageBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
