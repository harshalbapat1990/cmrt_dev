from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

EventType = Literal[
    "submitted",
    "approved",
    "rejected",
    "reopen_requested",
    "reopen_approved",
    "reopen_rejected",
]


class StageApprovalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stage_instance_id: UUID
    project_id: UUID
    event_type: EventType
    performed_by: Optional[UUID] = None
    performed_at: datetime
    justification: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    report_number: Optional[int] = None
    submission_period_id: Optional[UUID] = None
