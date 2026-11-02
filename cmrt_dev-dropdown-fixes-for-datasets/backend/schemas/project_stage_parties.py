from pydantic import BaseModel, UUID4
from typing import Optional

class ProjectStagePartyBase(BaseModel):
    project_stage_instance_id: UUID4
    organization_id: Optional[UUID4]
    joint_venture_id: Optional[UUID4]
    role: str
    role_note: Optional[str]
    contract_number: Optional[str]
    created_on: Optional[str]
    updated_on: Optional[str]

class ProjectStagePartyCreate(ProjectStagePartyBase):
    pass

class ProjectStagePartyUpdate(ProjectStagePartyBase):
    pass

class ProjectStagePartyInDB(ProjectStagePartyBase):
    id: UUID4

class ProjectStagePartyOut(ProjectStagePartyInDB):
    pass
