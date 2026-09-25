from __future__ import annotations
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Optional[EmailStr] = None  # local dev only; deployed auth derives email from Easy Auth headers
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    organisation_id: Optional[UUID] = None
    org_name: Optional[str] = None
    org_type: Optional[str] = None
    org_country: Optional[str] = None
    region: Optional[str] = None  # Jurisdiction name (e.g., "New South Wales")
    region_id: Optional[UUID] = None  # Jurisdiction ID
    is_proponent: bool = True
    org_admin_reason: Optional[str] = None
    accepted_pics: bool = False
    accepted_terms: bool = False

    @field_validator("org_type")
    @classmethod
    def validate_org_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from models.organizations import Organization_Type
        valid = {e.value for e in Organization_Type}
        if v.upper() not in valid:
            raise ValueError(f"org_type must be one of {sorted(valid)}")
        return v.upper()


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    organisation_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    region_id: Optional[UUID] = None
    org_created: bool = False
    org_admin_request_id: Optional[UUID] = None
    message: Optional[str] = None
