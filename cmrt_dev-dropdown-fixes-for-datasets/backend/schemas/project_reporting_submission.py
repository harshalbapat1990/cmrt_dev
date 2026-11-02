from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

ConstructionPeriodStatus = Literal[
    "in_progress",
    "awaiting_approval",
    "approved",
    "rejected",
    "reopen_requested",
]


class ProjectReportingSubmissionBase(BaseModel):
    project_id: UUID
    frequency: str = Field(max_length=50)
    period_label: str = Field(max_length=100)
    period_start_date: date
    period_end_date: date
    due_date: Optional[date] = None


class ProjectReportingSubmissionCreate(ProjectReportingSubmissionBase):
    pass


class ProjectReportingSubmissionUpdate(BaseModel):
    frequency: Optional[str] = Field(default=None, max_length=50)
    period_label: Optional[str] = Field(default=None, max_length=100)
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    due_date: Optional[date] = None


class ProjectReportingSubmissionOut(ProjectReportingSubmissionBase):
    id: UUID
    status: str = "in_progress"
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConstructionPeriodCreate(BaseModel):
    project_id: UUID
    stage_instance_id: UUID
    frequency: str = Field(max_length=50)
    period_label: str = Field(max_length=100)
    period_start_date: date
    period_end_date: date
    due_date: Optional[date] = None


class ConstructionPeriodOut(BaseModel):
    id: UUID
    project_id: UUID
    stage_instance_id: Optional[UUID] = None
    frequency: str
    period_label: str
    period_start_date: date
    period_end_date: date
    due_date: Optional[date] = None
    status: ConstructionPeriodStatus

    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None

    decision_by: Optional[UUID] = None
    decision_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    reopen_requested_by: Optional[UUID] = None
    reopen_requested_at: Optional[datetime] = None
    reopen_reason: Optional[str] = None
    exec_summary: Optional[str] = None
    exec_summary_author: Optional[str] = None
    exec_summary_date: Optional[datetime] = None

    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

    period_emissions_tco2e: Optional[Decimal] = None
    previous_period_emissions_tco2e: Optional[Decimal] = None
    all_periods_emissions_tco2e: Optional[Decimal] = None

    class Config:
        from_attributes = True
