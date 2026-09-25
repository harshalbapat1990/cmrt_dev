from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleMassBase(BaseModel):
    vehicle_class_id: UUID
    reference_gcm_tonnes: Optional[Decimal] = None
    max_payload_tonnes: Decimal
    gvm_tonnes: Decimal
    assumed_payload_pct: Decimal


class VehicleMassCreate(VehicleMassBase):
    pass


class VehicleMassUpdate(BaseModel):
    vehicle_class_id: Optional[UUID] = None
    reference_gcm_tonnes: Optional[Decimal] = None
    max_payload_tonnes: Optional[Decimal] = None
    gvm_tonnes: Optional[Decimal] = None
    assumed_payload_pct: Optional[Decimal] = None


class VehicleMassOut(VehicleMassBase):
    id: UUID
    vehicle_class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
