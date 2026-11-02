from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MaterialBase(BaseModel):
    name: str = Field(max_length=255)
    emissions_category_id: Optional[UUID] = None
    is_active: bool = True


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    emissions_category_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class MaterialOut(MaterialBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
