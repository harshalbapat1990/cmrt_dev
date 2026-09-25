from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UninterruptedVehicleBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: UUID
    gradient_m_per_km: Decimal = Decimal("0")
    curvature_deg_per_km: Decimal
    base_fuel_l_per_100km: Decimal
    k1: Decimal
    k2: Decimal
    k3: Decimal
    k4: Decimal
    k5: Decimal


class UninterruptedVehicleCreate(UninterruptedVehicleBase):
    pass


class UninterruptedVehicleUpdate(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: Optional[UUID] = None
    gradient_m_per_km: Optional[Decimal] = None
    curvature_deg_per_km: Optional[Decimal] = None
    base_fuel_l_per_100km: Optional[Decimal] = None
    k1: Optional[Decimal] = None
    k2: Optional[Decimal] = None
    k3: Optional[Decimal] = None
    k4: Optional[Decimal] = None
    k5: Optional[Decimal] = None


class UninterruptedVehicleOut(UninterruptedVehicleBase):
    id: UUID
    vehicle_class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
