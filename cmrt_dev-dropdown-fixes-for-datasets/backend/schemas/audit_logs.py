from datetime import datetime
from pydantic import BaseModel, ConfigDict, UUID4
from typing import Any, Dict, List, Optional


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    entity_type: str
    entity_id: UUID4
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    performed_by: Optional[UUID4] = None
    performed_by_org: Optional[UUID4] = None
    performed_at: Optional[datetime] = None
    event_metadata: Optional[Dict[str, Any]] = None
    performed_by_email: Optional[str] = None
    performed_by_org_name: Optional[str] = None
    entity_name: Optional[str] = None


class StageResubmissionAuditOut(BaseModel):
    has_prior_rejection: bool
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    stage_name: str
    rows: List[AuditLogOut]
