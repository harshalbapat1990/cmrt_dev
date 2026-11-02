from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VehicleClassBase(BaseModel):
    name: str
    sort_order: int = 0


class VehicleClassCreate(VehicleClassBase):
    pass


class VehicleClassUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class VehicleClassOut(VehicleClassBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
