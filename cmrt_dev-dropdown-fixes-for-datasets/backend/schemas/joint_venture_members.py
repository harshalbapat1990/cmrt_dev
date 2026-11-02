from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class JointVentureMemberBase(BaseModel):
    joint_venture_id: UUID
    organization_id: UUID
    ownership_pct: Optional[float] = None
    role: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class JointVentureMemberCreate(JointVentureMemberBase):
    pass


class JointVentureMemberOut(JointVentureMemberBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None