from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UserRoleBase(BaseModel):
    user_id: UUID
    role_id: UUID
    # scope_type must be one of GLOBAL / ORGANISATION / PROJECT / STAGE
    scope_type: str = "GLOBAL"
    scope_id: Optional[UUID] = None
    is_active: bool = True


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleUpdate(BaseModel):
    # Only is_active may be updated (revoke = is_active=False).
    # To change scope, deactivate old + create new assignment.
    is_active: Optional[bool] = None


class UserRoleOut(UserRoleBase):
    model_config = ConfigDict(from_attributes=True)    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None


class UserRoleEnrichedOut(BaseModel):
    user_role_id: str
    user_id: str
    user_email: str
    user_display_name: Optional[str] = None
    role_name: str
    scope_type: str
    scope_id: Optional[str] = None
    org_name: Optional[str] = None
    project_name: Optional[str] = None
    is_active: bool = True


class TransferOrgAdminRequest(BaseModel):
    from_user_role_id: UUID
    to_user_id: UUID


class AssignOrgAdminRequest(BaseModel):
    org_id: UUID
    user_id: UUID