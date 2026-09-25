
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

class OrganizationTypeEnum(str, Enum):
    DESIGNERS = "DESIGNERS"
    CONTRACTORS = "CONTRACTORS"
    PLATFORM_OPERATOR = "PLATFORM_OPERATOR"

class OrganizationBase(BaseModel):
    name: str = Field(max_length=255)
    organization_type: OrganizationTypeEnum
    is_active: bool = True

class OrganizationCreate(OrganizationBase):
    jurisdiction_id: Optional[UUID] = None
    region_id: Optional[UUID] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    organization_type: Optional[OrganizationTypeEnum] = None
    is_active: Optional[bool] = None
    jurisdiction_id: Optional[UUID] = None
    region_id: Optional[UUID] = None

class OrganizationOut(OrganizationBase):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    jurisdiction_id: Optional[UUID] = None
    jurisdiction_name: Optional[str] = None
    region_id: Optional[UUID] = None
    region_name: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
