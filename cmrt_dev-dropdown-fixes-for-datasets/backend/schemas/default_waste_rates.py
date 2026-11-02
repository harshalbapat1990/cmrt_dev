from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DefaultWasteRateBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    jurisdiction_id: UUID
    material_id: UUID
    waste_treatment_id: UUID
    applicable_lifecycle_module_code: Optional[str] = None
    basis: str
    rate: Decimal
    rate_unit_id: Optional[UUID] = None
    notes: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DefaultWasteRateCreate(DefaultWasteRateBase):
    pass


class DefaultWasteRateUpdate(BaseModel):
    jurisdiction_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    waste_treatment_id: Optional[UUID] = None
    applicable_lifecycle_module_code: Optional[str] = None
    basis: Optional[str] = None
    rate: Optional[Decimal] = None
    rate_unit_id: Optional[UUID] = None
    notes: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DefaultWasteRateOut(DefaultWasteRateBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True


class DefaultWasteRateWithNamesOut(DefaultWasteRateOut):
    material_name: Optional[str] = None
    waste_treatment_name: Optional[str] = None
    jurisdiction_name: Optional[str] = None
