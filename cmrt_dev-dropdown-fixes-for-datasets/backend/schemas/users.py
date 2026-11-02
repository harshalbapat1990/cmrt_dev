from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    oidc_sub: Optional[str] = None
    oidc_issuer: Optional[str] = None
    organization_id: Optional[UUID] = None
    password_hash: Optional[str] = None
    pics_accepted: bool = False
    pics_accepted_at: Optional[datetime] = None
    pics_version: Optional[int] = None
    terms_accepted: bool = False
    terms_accepted_at: Optional[datetime] = None
    terms_version: Optional[int] = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    oidc_sub: Optional[str] = None
    oidc_issuer: Optional[str] = None
    organization_id: Optional[UUID] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool
    oidc_sub: Optional[str] = None
    oidc_issuer: Optional[str] = None
    organization_id: Optional[UUID] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    pics_accepted: bool = False
    pics_accepted_at: Optional[datetime] = None
    pics_version: Optional[int] = None
    terms_accepted: bool = False
    terms_accepted_at: Optional[datetime] = None
    terms_version: Optional[int] = None
