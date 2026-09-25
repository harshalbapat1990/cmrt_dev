from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class EvUptakeFactorOut(BaseModel):
    id: UUID
    dataset_revision_id: UUID
    jurisdiction_id: UUID
    jurisdiction_name: Optional[str] = None
    scenario_code: str
    scenario_name: Optional[str] = None
    vehicle_category_code: str
    vehicle_category_name: Optional[str] = None
    energy_type_code: str
    energy_type_name: Optional[str] = None
    year: int
    uptake_pct: Optional[float] = None

    class Config:
        from_attributes = True


class EvUptakeFactorUpdate(BaseModel):
    uptake_pct: Optional[float] = None


class EvUptakeBulkCreate(BaseModel):
    dataset_revision_id: UUID
    jurisdiction_id: UUID
    scenario_code: str
    vehicle_category_code: str
    energy_type_code: str
    year_from: int
    year_to: int
