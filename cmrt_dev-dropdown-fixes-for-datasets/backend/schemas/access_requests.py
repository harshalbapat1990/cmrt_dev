from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccessRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: str
    target_user_id: Optional[UUID] = None
    requested_role_id: Optional[UUID] = None

    scope_type: str = "GLOBAL"
    scope_id: Optional[UUID] = None

    organisation_id: Optional[UUID] = None
    project_id: Optional[UUID] = None

    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AccessRequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_note: Optional[str] = None


class AccessRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_type: str
    status: str

    requester_user_id: Optional[UUID] = None
    target_user_id: Optional[UUID] = None
    requested_role_id: Optional[UUID] = None

    scope_type: str
    scope_id: Optional[UUID] = None

    organisation_id: Optional[UUID] = None
    project_id: Optional[UUID] = None

    reason: Optional[str] = None
    decision_note: Optional[str] = None
    reviewed_by_user_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class AccessRequestEnrichedOut(AccessRequestOut):
    requester_email: Optional[str] = None
    requester_display_name: Optional[str] = None
    organisation_name: Optional[str] = None
    project_name: Optional[str] = None
    project_class: Optional[str] = None
