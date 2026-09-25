from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class RolePermissionBase(BaseModel):
    role_id: UUID
    permission_id: UUID

class RolePermissionCreate(RolePermissionBase):
    pass

class RolePermissionUpdate(RolePermissionBase):
    pass

class RolePermissionOut(RolePermissionBase):
    model_config = ConfigDict(from_attributes=True)    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
