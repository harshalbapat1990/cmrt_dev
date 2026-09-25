from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ProjectOptionBase(BaseModel):
    project_id: UUID
    stage_instance_id: UUID
    report_number: int = 1
    option_number: int
    label: str
    is_default: bool = False


class ProjectOptionCreate(ProjectOptionBase):
    pass


class ProjectOptionUpdate(BaseModel):
    label: Optional[str] = None
    is_default: Optional[bool] = None


class ProjectOptionOut(ProjectOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: Optional[datetime] = None
    approval_status: str = 'draft'
    current_justification: Optional[str] = None
    exec_summary: Optional[str] = None
    exec_summary_author: Optional[str] = None
    exec_summary_date: Optional[datetime] = None
    total_emissions_tco2e: Optional[Decimal] = None
