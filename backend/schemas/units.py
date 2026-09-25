from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class UnitBase(BaseModel):
    code: str = Field(max_length=50)
    label: Optional[str] = Field(default=None, max_length=100)


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    code: Optional[str] = Field(default=None, max_length=50)
    label: Optional[str] = Field(default=None, max_length=100)


class UnitOut(UnitBase):
    id: UUID

    class Config:
        from_attributes = True
