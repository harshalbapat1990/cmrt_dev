from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InterruptedVehicleBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: UUID
    coefficient_a: Decimal
    coefficient_b: Decimal


class InterruptedVehicleCreate(InterruptedVehicleBase):
    pass


class InterruptedVehicleUpdate(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: Optional[UUID] = None
    coefficient_a: Optional[Decimal] = None
    coefficient_b: Optional[Decimal] = None


class InterruptedVehicleOut(InterruptedVehicleBase):
    id: UUID
    vehicle_class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
