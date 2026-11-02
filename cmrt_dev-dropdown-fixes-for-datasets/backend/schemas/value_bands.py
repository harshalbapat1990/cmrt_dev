from typing import Optional
from pydantic import BaseModel, Field


class ValueBandBase(BaseModel):
    code: str = Field(max_length=50)
    sort_order: Optional[int] = None


class ValueBandCreate(ValueBandBase):
    pass


class ValueBandUpdate(BaseModel):
    sort_order: Optional[int] = None


class ValueBandOut(ValueBandBase):
    class Config:
        from_attributes = True
