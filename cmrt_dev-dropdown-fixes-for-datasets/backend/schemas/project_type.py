
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

class ProjectTypeBase(BaseModel):
    name: str = Field(max_length=50)
    is_active: bool = True

class ProjectTypeCreate(ProjectTypeBase):
    pass

class ProjectTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None

class ProjectTypeOut(ProjectTypeBase):
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    class Config:
        from_attributes = True

# ---- typecast
class ProjectTypecastBase(BaseModel):
    project_type_id: UUID
    name: str = Field(max_length=100)
    is_maintenance: bool = False
    is_active: bool = True

class ProjectTypecastCreate(ProjectTypecastBase):
    pass

class ProjectTypecastUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    is_maintenance: Optional[bool] = None
    is_active: Optional[bool] = None

class ProjectTypecastOut(ProjectTypecastBase):
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    
    class Config:
        from_attributes = True