from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class ProjectRoleInfo(BaseModel):
    project_id: UUID
    project_name: str
    role_name: str
    user_role_id: UUID
    is_active: bool


class OrgUserWithRoles(BaseModel):
    user_id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool
    project_roles: List[ProjectRoleInfo]
    has_org_admin_role: bool = False
    org_admin_user_role_id: Optional[UUID] = None


class AddProjectAdminRequest(BaseModel):
    user_id: UUID


class ProjectAdminResponse(BaseModel):
    user_id: UUID
    project_id: UUID
    role_name: str
    user_role_id: UUID
    message: str


class AddOrgAdminRequest(BaseModel):
    user_id: UUID


class OrgAdminResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    role_name: str
    user_role_id: UUID
    message: str
