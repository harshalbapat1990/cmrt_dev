from datetime import date, datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

RevisionStatus = Literal["draft", "published", "deprecated", "archived"]
RevisionScopeType = Literal["DEFAULT", "ORG", "PROJECT"]


class DatasetRevisionBase(BaseModel):
    name: str = Field(max_length=255)
    applicable_from: Optional[date] = None
    applicable_to: Optional[date] = None
    notes: Optional[str] = None


class DatasetRevisionCreate(DatasetRevisionBase):
    created_by: Optional[UUID] = None
    scope_type: RevisionScopeType = "DEFAULT"
    scope_id: Optional[UUID] = None
    parent_revision_id: Optional[UUID] = None


class DatasetRevisionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    applicable_from: Optional[date] = None
    applicable_to: Optional[date] = None
    notes: Optional[str] = None


class DatasetRevisionBranch(BaseModel):
    name: str = Field(max_length=255)
    notes: Optional[str] = None
    scope_type: RevisionScopeType = "DEFAULT"
    scope_id: Optional[UUID] = None
    parent_revision_id: Optional[UUID] = None


class DatasetRevisionOut(DatasetRevisionBase):
    id: UUID
    status: RevisionStatus
    scope_type: RevisionScopeType
    scope_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    parent_revision_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class DatasetRevisionUnpublishRequest(BaseModel):
    confirm_bound_project_ids: list[UUID]


class BoundProjectOut(BaseModel):
    project_id: UUID
    project_name: str


class DatasetRevisionBindingsOut(BaseModel):
    revision_id: UUID
    scope_type: RevisionScopeType
    status: RevisionStatus
    projects: list[BoundProjectOut]


class ProjectRecalculationOut(BaseModel):
    project_id: UUID
    project_name: str
    status: Literal["recalculated", "failed"]
    missing_data: list[dict[str, Any]] = Field(default_factory=list)
    calculation_errors: list[dict[str, Any]] = Field(default_factory=list)
    recalculated_count: int = 0


class DatasetRevisionPublishOut(DatasetRevisionOut):
    project_recalculations: list[ProjectRecalculationOut] = Field(default_factory=list)
