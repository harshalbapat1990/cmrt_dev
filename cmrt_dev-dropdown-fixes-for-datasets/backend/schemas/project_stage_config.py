from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ProjectStageEnum(str, Enum):
    BUSINESS_CASE = "BUSINESS_CASE"
    DESIGN = "DESIGN"
    CONSTRUCTION = "CONSTRUCTION"


class ReportFrequencyEnum(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BI_MONTHLY = "BI_MONTHLY"
    ANNUAL = "ANNUAL"


class ProjectStageConfigBase(BaseModel):
    project_id: UUID
    stage: ProjectStageEnum
    enabled: bool = False
    num_reports_required: Optional[int] = None
    frequency: Optional[ReportFrequencyEnum] = None
    min_requirements: Optional[Dict[str, Any]] = None


class ProjectStageConfigCreate(ProjectStageConfigBase):
    pass


class ProjectStageConfigOut(ProjectStageConfigBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None