from datetime import date, datetime
from typing import Literal, Optional
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
