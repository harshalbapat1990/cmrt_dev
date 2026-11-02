from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleEnergyConversionRateBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: UUID
    ev_projection_category: str
    primary_ice_fuel: str
    hybrid_fuel_savings_pct: Decimal
    phev_fuel_savings_pct: Decimal
    bev_energy_shift_kwh_per_l: Decimal
    fcev_hydrogen_consumption_kwh_per_l: Decimal
    source_comments: Optional[str] = None


class VehicleEnergyConversionRateCreate(VehicleEnergyConversionRateBase):
    pass


class VehicleEnergyConversionRateUpdate(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    vehicle_class_id: Optional[UUID] = None
    ev_projection_category: Optional[str] = None
    primary_ice_fuel: Optional[str] = None
    hybrid_fuel_savings_pct: Optional[Decimal] = None
    phev_fuel_savings_pct: Optional[Decimal] = None
    bev_energy_shift_kwh_per_l: Optional[Decimal] = None
    fcev_hydrogen_consumption_kwh_per_l: Optional[Decimal] = None
    source_comments: Optional[str] = None


class VehicleEnergyConversionRateOut(VehicleEnergyConversionRateBase):
    id: UUID
    vehicle_class_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
