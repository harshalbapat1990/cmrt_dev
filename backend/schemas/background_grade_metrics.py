from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class BackgroundGradeMetricBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    grade_id: int
    jurisdiction_id: Optional[UUID] = None
    mastertype_id: Optional[UUID] = None
    typecast_id: Optional[UUID] = None
    emissions_category_id: Optional[UUID] = None
    emissions_subcategory_id: Optional[UUID] = None
    emissions_source: Optional[str] = None
    lifecycle_module_code: Optional[str] = None
    ghg_scope_id: Optional[int] = None
    metric_type_id: UUID
    band_code: Optional[str] = None
    unit_id: Optional[UUID] = None
    value: Optional[Decimal] = None
    assumed_quantity_default: Optional[Decimal] = None
    source: Optional[str] = None


class BackgroundGradeMetricCreate(BackgroundGradeMetricBase):
    pass


class BackgroundGradeMetricUpdate(BaseModel):
    value: Optional[Decimal] = None
    assumed_quantity_default: Optional[Decimal] = None
    source: Optional[str] = None
    band_code: Optional[str] = None
    unit_id: Optional[UUID] = None


class BackgroundGradeMetricOut(BackgroundGradeMetricBase):
    id: UUID
    is_active: bool = True
    created_at: datetime
    grade_name: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    mastertype_name: Optional[str] = None
    typecast_name: Optional[str] = None
    emissions_category: Optional[str] = None
    emissions_subcategory: Optional[str] = None
    lifecycle_module_name: Optional[str] = None
    ghg_scope_name: Optional[str] = None
    metric_type_code: Optional[str] = None
    metric_type_name: Optional[str] = None
    unit_code: Optional[str] = None
    unit_label: Optional[str] = None

    class Config:
        from_attributes = True
