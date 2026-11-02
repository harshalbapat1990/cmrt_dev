from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class PermissionBase(BaseModel):
    name: str
    description: Optional[str]
    created_on: Optional[str]
    updated_on: Optional[str]
    
class PermissionCreate(PermissionBase):
    pass

class PermissionUpdate(PermissionBase):
    pass

class PermissionOut(PermissionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
