from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class BaseCaseAssumptionBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    name: str
    emissions_category_id: UUID
    default_value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    is_anz_default: bool = True
    notes: Optional[str] = None


class BaseCaseAssumptionCreate(BaseCaseAssumptionBase):
    pass


class BaseCaseAssumptionUpdate(BaseModel):
    name: Optional[str] = None
    emissions_category_id: Optional[UUID] = None
    default_value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    is_anz_default: Optional[bool] = None
    notes: Optional[str] = None


class BaseCaseAssumptionOut(BaseCaseAssumptionBase):
    id: UUID

    class Config:
        from_attributes = True
