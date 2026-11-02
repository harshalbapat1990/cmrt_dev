from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WasteTreatmentBase(BaseModel):
    name: str = Field(max_length=255)
    is_active: bool = True


class WasteTreatmentCreate(WasteTreatmentBase):
    pass


class WasteTreatmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class WasteTreatmentOut(WasteTreatmentBase):
    id: UUID

    class Config:
        from_attributes = True
