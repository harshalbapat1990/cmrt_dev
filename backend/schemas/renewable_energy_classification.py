from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RenewableEnergyClassificationBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    emissions_source: str
    classification: str
    notes: Optional[str] = None


class RenewableEnergyClassificationCreate(RenewableEnergyClassificationBase):
    pass


class RenewableEnergyClassificationUpdate(BaseModel):
    classification: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class RenewableEnergyClassificationOut(RenewableEnergyClassificationBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True
