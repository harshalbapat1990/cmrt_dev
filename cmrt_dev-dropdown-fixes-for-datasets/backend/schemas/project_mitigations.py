from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectMitigationCreate(BaseModel):
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: Optional[UUID] = None
    submission_stage: str = Field(..., max_length=32)
    name: str = Field(..., max_length=512)
    mitigation_type: str = Field(..., max_length=32)
    lifecycle_phase: str = Field(..., max_length=64)
    lifecycle_phase_label: str = Field(..., max_length=128)
    notes: Optional[str] = None
    group_label: Optional[str] = Field(None, max_length=512)


class ProjectMitigationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=512)
    mitigation_type: Optional[str] = Field(None, max_length=32)
    lifecycle_phase: Optional[str] = Field(None, max_length=64)
    lifecycle_phase_label: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    group_label: Optional[str] = Field(None, max_length=512)


class ProjectMitigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    project_option_id: Optional[UUID] = None
    submission_stage: str
    name: str
    mitigation_type: str
    lifecycle_phase: str
    lifecycle_phase_label: str
    notes: Optional[str] = None
    group_label: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None