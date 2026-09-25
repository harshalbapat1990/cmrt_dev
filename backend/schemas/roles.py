from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict  

class RoleBase(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class RoleOut(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    