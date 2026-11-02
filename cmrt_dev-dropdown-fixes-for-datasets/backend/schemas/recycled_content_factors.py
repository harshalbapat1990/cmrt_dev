from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class RecycledContentFactorBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    emissions_sub_category_id: Optional[UUID] = None
    emissions_source: str
    recycled_content_pct: Optional[Decimal] = None
    reused_content_pct: Optional[Decimal] = None
    notes: Optional[str] = None

    @field_validator("recycled_content_pct", "reused_content_pct")
    @classmethod
    def _non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError("Percentage value must be non-negative")
        return v


class RecycledContentFactorCreate(RecycledContentFactorBase):
    pass


class RecycledContentFactorUpsert(RecycledContentFactorBase):
    """Create or update by (jurisdiction_id, emissions_source, dataset_revision_id)."""


class RecycledContentFactorUpdate(BaseModel):
    emissions_sub_category_id: Optional[UUID] = None
    emissions_source: Optional[str] = None
    recycled_content_pct: Optional[Decimal] = None
    reused_content_pct: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("recycled_content_pct", "reused_content_pct")
    @classmethod
    def _non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError("Percentage value must be non-negative")
        return v


class RecycledContentFactorOut(RecycledContentFactorBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True
