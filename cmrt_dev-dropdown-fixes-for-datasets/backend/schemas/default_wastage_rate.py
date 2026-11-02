from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RelatedJurisdiction(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class RelatedMaterial(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class RelatedDatasetRevision(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class DefaultWastageRateBase(BaseModel):
    jurisdiction_id: UUID
    material_id: UUID
    construction_wastage_rate: Decimal
    recycling_rate: Decimal
    landfill_rate: Decimal
    source: Optional[str] = None


class DefaultWastageRateCreate(DefaultWastageRateBase):
    dataset_revision_id: Optional[UUID] = None


class DefaultWastageRateUpdate(BaseModel):
    jurisdiction_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    construction_wastage_rate: Optional[Decimal] = None
    recycling_rate: Optional[Decimal] = None
    landfill_rate: Optional[Decimal] = None
    source: Optional[str] = None
    dataset_revision_id: Optional[UUID] = None


class DefaultWastageRateOut(DefaultWastageRateBase):
    id: UUID
    dataset_revision_id: Optional[UUID] = None
    jurisdiction: RelatedJurisdiction
    material: RelatedMaterial
    dataset_revision: Optional[RelatedDatasetRevision] = None

    class Config:
        from_attributes = True
