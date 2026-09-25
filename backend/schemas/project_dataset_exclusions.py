from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ProjectDatasetExclusionBase(BaseModel):
    project_id: UUID
    metric_id: UUID
    excluded_from_revision: bool = True
    reason: Optional[str] = None


class ProjectDatasetExclusionCreate(ProjectDatasetExclusionBase):
    pass


class ProjectDatasetExclusionUpdate(BaseModel):
    excluded_from_revision: Optional[bool] = None
    reason: Optional[str] = None


class ProjectDatasetExclusionOut(ProjectDatasetExclusionBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
