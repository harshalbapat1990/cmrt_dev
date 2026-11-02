from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from schemas.anz_reporting_stages import AnzReportingStageOut


class JurisdictionReportingStageBase(BaseModel):
    jurisdiction_id: UUID
    anz_reporting_stage_id: UUID
    name: str = Field(max_length=255)
    sequence: int


class JurisdictionReportingStageCreate(JurisdictionReportingStageBase):
    pass


class JurisdictionReportingStageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    sequence: Optional[int] = None
    anz_reporting_stage_id: Optional[UUID] = None


class JurisdictionReportingStageOut(JurisdictionReportingStageBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
