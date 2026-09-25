from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class EmissionsCategoryBase(BaseModel):
    name: str = Field(max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    scope: Optional[int] = None
    parent_category_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool = True
    sort_order: Optional[int] = None


class EmissionsCategoryCreate(EmissionsCategoryBase):
    pass


class EmissionsCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    scope: Optional[int] = None
    parent_category_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class EmissionsCategoryOut(EmissionsCategoryBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
