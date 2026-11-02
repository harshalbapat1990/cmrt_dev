from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProponentAssumptionOverrideBase(BaseModel):
    proponent_org_id: UUID
    assumption_id: UUID
    value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    effective_from: date
    effective_to: Optional[date] = None


class ProponentAssumptionOverrideCreate(ProponentAssumptionOverrideBase):
    pass


class ProponentAssumptionOverrideUpdate(BaseModel):
    proponent_org_id: Optional[UUID] = None
    assumption_id: Optional[UUID] = None
    value: Optional[Decimal] = None
    unit_id: Optional[UUID] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class ProponentAssumptionOverrideOut(ProponentAssumptionOverrideBase):
    id: UUID

    class Config:
        from_attributes = True
