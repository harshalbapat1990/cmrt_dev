from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, computed_field


class ProjectStageEnum(str, Enum):
    BUSINESS_CASE = "BUSINESS_CASE"
    DESIGN = "DESIGN"
    CONSTRUCTION = "CONSTRUCTION"
    RECURRING = "RECURRING"


ApprovalStatus = Literal[
    "draft",
    "submitted",
    "in_review",
    "tech_approved",
    "final_approved",
    "rejected",
    "pending_reopen",
]

LOCKED_STATUSES = {"submitted", "in_review", "tech_approved", "final_approved", "pending_reopen"}


class ProjectStageInstanceBase(BaseModel):
    project_id: UUID
    stage: ProjectStageEnum


class ProjectStageInstanceCreate(ProjectStageInstanceBase):
    pass


class ProjectStageInstanceOut(ProjectStageInstanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_name: Optional[str] = None
    sequence: int = 0
    num_reports_required: Optional[int] = None
    frequency: Optional[str] = None
    approval_status: ApprovalStatus = "draft"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    technical_approved_at: Optional[datetime] = None
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    current_justification: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

    @computed_field
    @property
    def is_locked(self) -> bool:
        return self.approval_status in LOCKED_STATUSES