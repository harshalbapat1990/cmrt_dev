from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class RelatedUnit(BaseModel):
    id: UUID
    code: str
    label: Optional[str] = None

    class Config:
        from_attributes = True


class UnitConversionBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    from_unit_id: UUID
    to_unit_id: UUID
    factor: Decimal


class UnitConversionCreate(UnitConversionBase):
    pass


class UnitConversionUpdate(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    factor: Optional[Decimal] = None
    from_unit_id: Optional[UUID] = None
    to_unit_id: Optional[UUID] = None


class UnitConversionOut(UnitConversionBase):
    id: UUID
    from_unit: RelatedUnit
    to_unit: RelatedUnit

    class Config:
        from_attributes = True
