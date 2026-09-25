from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FreightRailFactorOut(BaseModel):
    id: UUID
    dataset_revision_id: UUID
    train_type: str
    terrain: str
    fuel_consumption_l_per_000_gtk: Optional[float] = None
    source_note: Optional[str] = None

    class Config:
        from_attributes = True


class FreightRailFactorUpdate(BaseModel):
    fuel_consumption_l_per_000_gtk: Optional[float] = None
    source_note: Optional[str] = None
