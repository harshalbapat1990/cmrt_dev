"""Pydantic schemas for the BAU concrete mix designs dataset."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConcreteMixAssumptionBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    bau_scm_content_pct: Decimal = Field(
        default=Decimal("0"),
        description="BAU SCM content as a fraction in [0, 1] (e.g. 0.30 = 30%)",
    )
    default_max_fly_ash_pct: Decimal = Field(
        default=Decimal("0.30"),
        description="Default max fly ash as a fraction in [0, 1] (e.g. 0.30 = 30%)",
    )

    @field_validator("bau_scm_content_pct", "default_max_fly_ash_pct")
    @classmethod
    def _ensure_fraction_range(cls, v: Decimal) -> Decimal:
        if v is None:
            return v
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("Percentage must be a fraction between 0 and 1 inclusive (e.g. 0.30 for 30%)")
        return v


class ConcreteMixAssumptionUpdate(BaseModel):
    bau_scm_content_pct: Optional[Decimal] = None
    default_max_fly_ash_pct: Optional[Decimal] = None

    @field_validator("bau_scm_content_pct", "default_max_fly_ash_pct")
    @classmethod
    def _ensure_fraction_range(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("Percentage must be a fraction between 0 and 1 inclusive (e.g. 0.30 for 30%)")
        return v


class ConcreteMixAssumptionOut(ConcreteMixAssumptionBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True


class ConcreteMixDesignBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    component_code: str
    component_label: str
    display_order: int = 0
    strength_20_kg_m3: Optional[Decimal] = None
    strength_25_kg_m3: Optional[Decimal] = None
    strength_32_kg_m3: Optional[Decimal] = None
    strength_40_kg_m3: Optional[Decimal] = None
    strength_50_kg_m3: Optional[Decimal] = None
    strength_65_kg_m3: Optional[Decimal] = None
    strength_80_kg_m3: Optional[Decimal] = None
    strength_100_kg_m3: Optional[Decimal] = None


class ConcreteMixDesignUpdate(BaseModel):
    strength_20_kg_m3: Optional[Decimal] = None
    strength_25_kg_m3: Optional[Decimal] = None
    strength_32_kg_m3: Optional[Decimal] = None
    strength_40_kg_m3: Optional[Decimal] = None
    strength_50_kg_m3: Optional[Decimal] = None
    strength_65_kg_m3: Optional[Decimal] = None
    strength_80_kg_m3: Optional[Decimal] = None
    strength_100_kg_m3: Optional[Decimal] = None

    @field_validator(
        "strength_20_kg_m3",
        "strength_25_kg_m3",
        "strength_32_kg_m3",
        "strength_40_kg_m3",
        "strength_50_kg_m3",
        "strength_65_kg_m3",
        "strength_80_kg_m3",
        "strength_100_kg_m3",
    )
    @classmethod
    def _non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v < Decimal("0"):
            raise ValueError("Mix content values must be non-negative")
        return v


class ConcreteMixDesignOut(ConcreteMixDesignBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True


class ConcreteMixDesignBundle(BaseModel):
    """Convenience response combining the assumptions row and all design rows."""

    assumptions: ConcreteMixAssumptionOut
    rows: List[ConcreteMixDesignOut]


class ConcreteMixAssumptionsUpdateResult(BaseModel):
    assumptions: ConcreteMixAssumptionOut
    recalculated_rows: List[ConcreteMixDesignOut] = []


class ConcreteMixDesignUpdateResult(BaseModel):
    row: ConcreteMixDesignOut
    recalculated_rows: List[ConcreteMixDesignOut] = []
