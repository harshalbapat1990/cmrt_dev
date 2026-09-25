
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

# -------- EmissionEntry --------
class EmissionEntryBase(BaseModel):
    project_id: UUID
    project_reporting_submission_id: UUID
    emissions_sub_category_id: UUID
    emission_source_id: UUID
    measurement_unit_id: UUID
    emission_factor_id: UUID
    data_quality: str = Field(max_length=50)
    quantity: Decimal
    emissions_tco2e: Decimal
    notes: Optional[str] = Field(default=None, max_length=100)
    submitted_by_user_id: UUID

class EmissionEntryCreate(EmissionEntryBase):
    pass

class EmissionEntryUpdate(BaseModel):
    project_id: Optional[UUID] = None
    project_reporting_submission_id: Optional[UUID] = None
    emissions_sub_category_id: Optional[UUID] = None
    emission_source_id: Optional[UUID] = None
    measurement_unit_id: Optional[UUID] = None
    emission_factor_id: Optional[UUID] = None
    data_quality: Optional[str] = Field(default=None, max_length=50)
    quantity: Optional[Decimal] = None
    emissions_tco2e: Optional[Decimal] = None
    notes: Optional[str] = Field(default=None, max_length=100)

class EmissionEntryOut(EmissionEntryBase):
    id: UUID
    submitted_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True

# -------- EmissionEntrySummary --------
class EmissionEntrySummaryBase(BaseModel):
    project_id: UUID
    project_reporting_submission_id: UUID
    summary: Optional[str] = Field(default=None, max_length=1000)
    submitted_by_user_id: UUID

class EmissionEntrySummaryCreate(EmissionEntrySummaryBase):
    pass

class EmissionEntrySummaryUpdate(BaseModel):
    summary: Optional[str] = Field(default=None, max_length=1000)

class EmissionEntrySummaryOut(EmissionEntrySummaryBase):
    id: UUID
    submitted_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True
