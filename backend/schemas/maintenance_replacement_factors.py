from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RelatedUnit(BaseModel):
    id: UUID
    code: str
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class MaintenanceReplacementFactorOut(BaseModel):
    id: UUID
    dataset_revision_id: UUID
    jurisdiction_id: Optional[UUID]
    jurisdiction_name: Optional[str]
    activity_type: str
    item: str
    unit_id: Optional[UUID]
    unit: Optional[RelatedUnit]
    emissions_intensity_tco2e: Optional[Decimal]
    default_frequency_years: Optional[int]
    source_note: Optional[str]

    model_config = {"from_attributes": True}


class MaintenanceReplacementFactorUpdate(BaseModel):
    emissions_intensity_tco2e: Optional[Decimal] = None
    default_frequency_years: Optional[int] = None
    source_note: Optional[str] = None
