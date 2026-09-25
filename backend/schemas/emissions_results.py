from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EmissionsResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_stage_instance_id: UUID
    activity_data_id: UUID
    lifecycle_module_code: Optional[str] = None
    value: Decimal
    unit_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
