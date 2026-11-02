from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class VepmFactorOut(BaseModel):
    id: UUID
    dataset_revision_id: UUID
    year: int
    speed_kmh: int
    fleet_average_co2e_g_km: Optional[float] = None
    light_vehicle_co2e_g_km: Optional[float] = None
    heavy_vehicle_co2e_g_km: Optional[float] = None
    bus_co2e_g_km: Optional[float] = None

    class Config:
        from_attributes = True


class VepmFactorUpdate(BaseModel):
    fleet_average_co2e_g_km: Optional[float] = None
    light_vehicle_co2e_g_km: Optional[float] = None
    heavy_vehicle_co2e_g_km: Optional[float] = None
    bus_co2e_g_km: Optional[float] = None
