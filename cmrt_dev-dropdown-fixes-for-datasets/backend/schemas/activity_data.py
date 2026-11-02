from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ActivityDataBase(BaseModel):
    project_id: UUID
    project_stage_instance_id: UUID
    dataset_revision_id: Optional[UUID] = None
    metric_natural_key: Optional[Dict[str, Any]] = None
    # Deprecated API compatibility: frontend/tests may still send metric_id.
    # It is resolved to metric_natural_key before persistence.
    metric_id: Optional[UUID] = None
    quantity: Decimal
    unit_id: Optional[UUID] = None
    ui_table_key: str
    project_option_id: Optional[UUID] = None
    component_id: Optional[UUID] = None
    lifecycle_module_code: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None
    submission_period_id: Optional[UUID] = None
    project_mitigation_id: Optional[UUID] = None


class ActivityDataCreate(ActivityDataBase):
    created_by: Optional[UUID] = None


class ActivityDataUpdate(BaseModel):
    """All fields optional for PATCH semantics."""
    quantity: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    dataset_revision_id: Optional[UUID] = None
    metric_natural_key: Optional[Dict[str, Any]] = None
    # Deprecated API compatibility; never persisted to activity_data.
    metric_id: Optional[UUID] = None
    project_option_id: Optional[UUID] = None
    lifecycle_module_code: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None


class ActivityDataOut(ActivityDataBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # Deprecated API compatibility; populated from metric_natural_key when possible.
    metric_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    emissions_tco2e: Optional[Decimal] = None