from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class JointVentureBase(BaseModel):
    name: str
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

class JointVentureCreate(JointVentureBase):
    pass

class JointVentureUpdate(JointVentureBase):
    pass

class JointVentureInDB(JointVentureBase):
    id: UUID

class JointVentureOut(JointVentureBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
