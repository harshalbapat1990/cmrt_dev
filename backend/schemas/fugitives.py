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


class RelatedDatasetRevision(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class FugitiveBase(BaseModel):
    jurisdiction_id: UUID
    equipment_type: str
    default_annual_leakage_rate: Decimal
    source_comments: Optional[str] = None


class FugitiveCreate(FugitiveBase):
    dataset_revision_id: Optional[UUID] = None


class FugitiveUpdate(BaseModel):
    equipment_type: Optional[str] = None
    default_annual_leakage_rate: Optional[Decimal] = None
    source_comments: Optional[str] = None
    jurisdiction_id: Optional[UUID] = None
    dataset_revision_id: Optional[UUID] = None


class FugitiveOut(FugitiveBase):
    id: UUID
    dataset_revision_id: Optional[UUID] = None
    jurisdiction: RelatedJurisdiction
    dataset_revision: Optional[RelatedDatasetRevision] = None

    class Config:
        from_attributes = True
