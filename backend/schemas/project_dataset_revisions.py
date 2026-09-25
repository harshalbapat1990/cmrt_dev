from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from schemas.dataset_revisions import DatasetRevisionOut


class ProjectDatasetRevisionBase(BaseModel):
    project_id: UUID
    dataset_revision_id: UUID
    notes: Optional[str] = None


class ProjectDatasetRevisionCreate(ProjectDatasetRevisionBase):
    pass


class ProjectDatasetRevisionUpdate(BaseModel):
    is_locked: Optional[bool] = None
    notes: Optional[str] = None


class ProjectDatasetRevisionOut(ProjectDatasetRevisionBase):
    id: UUID
    applied_at: datetime
    is_locked: bool
    revision: Optional[DatasetRevisionOut] = None

    class Config:
        from_attributes = True
