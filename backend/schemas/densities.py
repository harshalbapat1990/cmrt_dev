from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


DatasetType = Literal["component", "detailed"]


class RelatedJurisdiction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class RelatedDatasetRevision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class RelatedEmissionsCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None = None


class RelatedUnit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    label: str | None = None


class DensityBase(BaseModel):
    dataset_revision_id: UUID
    jurisdiction_id: UUID
    dataset: DatasetType
    record_key: str = Field(min_length=1)

    # Component-level
    group: str | None = None
    sub_group: str | None = None
    item: str | None = None
    item_description: str | None = None

    # Detailed-level
    emissions_category_id: UUID | None = None
    emissions_sub_category_id: UUID | None = None
    emissions_source: str | None = None

    # Measurement
    density: Decimal | None = None
    unit_id: UUID
    source: str | None = None


class DensityCreate(DensityBase):
    pass


class DensityUpdate(BaseModel):
    jurisdiction_id: UUID | None = None
    dataset: DatasetType | None = None
    record_key: str | None = Field(default=None, min_length=1)
    group: str | None = None
    sub_group: str | None = None
    item: str | None = None
    item_description: str | None = None
    emissions_category_id: UUID | None = None
    emissions_sub_category_id: UUID | None = None
    emissions_source: str | None = None
    density: Decimal | None = None
    unit_id: UUID | None = None
    source: str | None = None


class DensityOut(DensityBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    jurisdiction: RelatedJurisdiction | None = None
    dataset_revision: RelatedDatasetRevision | None = None
    emissions_category: RelatedEmissionsCategory | None = None
    emissions_sub_category: RelatedEmissionsCategory | None = None
    unit: RelatedUnit
