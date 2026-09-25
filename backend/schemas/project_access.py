from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StageAccess(str, Enum):
    VIEW = "VIEW"
    EDIT = "EDIT"


class ProjectStageAccessOut(BaseModel):
    stage_instance_id: UUID
    stage: str
    stage_label: str
    sequence: int = 0

    # NONE is used when this object describes a project stage rather than
    # a user's assignment.
    access: str

    # For a user assignment, this points to the corresponding user_roles row.
    user_role_id: UUID | None = None


class ProjectAccessMemberOut(BaseModel):
    user_id: UUID
    display_name: str
    email: str

    assignments: List[ProjectStageAccessOut]


class ProjectAccessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    project_name: str

    # All stages actually belonging to this project.
    stages: List[ProjectStageAccessOut]

    # Only users who actually have project access.
    members: List[ProjectAccessMemberOut]


class StageAccessAssignmentIn(BaseModel):
    stage_instance_id: UUID
    access: StageAccess


class UpdateUserStageAccessIn(BaseModel):
    """
    Complete desired stage-access state for one user.

    An omitted stage means NO ACCESS.
    """

    assignments: List[StageAccessAssignmentIn] = Field(
        default_factory=list
    )