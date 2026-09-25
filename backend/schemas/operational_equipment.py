from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, computed_field


class OperationalEquipmentBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    group_name: str
    item: str
    power_kw: Decimal
    hours_per_day: Decimal
    days_per_year: Decimal
    source: Optional[str] = None


class OperationalEquipmentCreate(OperationalEquipmentBase):
    pass


class OperationalEquipmentUpdate(BaseModel):
    group_name: Optional[str] = None
    item: Optional[str] = None
    power_kw: Optional[Decimal] = None
    hours_per_day: Optional[Decimal] = None
    days_per_year: Optional[Decimal] = None
    source: Optional[str] = None


class OperationalEquipmentOut(OperationalEquipmentBase):
    id: UUID
    is_active: bool = True

    @computed_field 
    @property
    def annual_electricity_consumption_mwh(self) -> Decimal:
        return (self.power_kw * self.hours_per_day * self.days_per_year / Decimal("1000")).quantize(
            Decimal("0.0001")
        )

    class Config:
        from_attributes = True
