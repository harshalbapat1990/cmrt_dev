from typing import Optional
from pydantic import BaseModel, Field


class GradeDefinitionBase(BaseModel):
    id: int
    name: str = Field(max_length=255)


class GradeDefinitionCreate(GradeDefinitionBase):
    pass


class GradeDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class GradeDefinitionOut(GradeDefinitionBase):
    class Config:
        from_attributes = True
