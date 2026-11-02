from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RelatedUnit(BaseModel):
    id: UUID
    code: str
    label: Optional[str] = None

    class Config:
        from_attributes = True


class RelatedDatasetRevision(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class EnergyDensityConversionBase(BaseModel):
    category: str
    name: str
    unit_id: UUID
    energy_density: Decimal
    source_comments: Optional[str] = None


class EnergyDensityConversionCreate(EnergyDensityConversionBase):
    dataset_revision_id: Optional[UUID] = None


class EnergyDensityConversionUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    unit_id: Optional[UUID] = None
    energy_density: Optional[Decimal] = None
    source_comments: Optional[str] = None
    dataset_revision_id: Optional[UUID] = None


class EnergyDensityConversionOut(EnergyDensityConversionBase):
    id: UUID
    dataset_revision_id: Optional[UUID] = None
    unit: RelatedUnit
    dataset_revision: Optional[RelatedDatasetRevision] = None

    class Config:
        from_attributes = True
