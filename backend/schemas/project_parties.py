from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ProjectPartyBase(BaseModel):
    project_id: UUID
    organization_id: Optional[UUID] = None
    joint_venture_id: Optional[UUID] = None
    role: str
    role_note: Optional[str] = None
    contract_number: Optional[str] = None


class ProjectPartyCreate(ProjectPartyBase):
    pass


class ProjectPartyOut(ProjectPartyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None