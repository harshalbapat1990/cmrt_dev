from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Literal, Optional
from uuid import UUID
from pydantic import BaseModel

# Enforced change_type values.
ChangeType = Literal["UPDATE", "ADD", "REMOVE"]


class DatasetRevisionChangeBase(BaseModel):
    dataset_revision_id: UUID
    metric_natural_key: Dict[str, Any] = {}
    change_type: ChangeType
    old_value: Optional[Decimal] = None
    new_value: Optional[Decimal] = None
    reason: Optional[str] = None


class DatasetRevisionChangeCreate(DatasetRevisionChangeBase):
    changed_by: Optional[UUID] = None


class DatasetRevisionChangeOut(DatasetRevisionChangeBase):
    id: UUID
    changed_by: Optional[UUID] = None
    changed_at: datetime

    class Config:
        from_attributes = True
