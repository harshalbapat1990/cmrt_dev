from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from enum import Enum
from datetime import datetime

class AreaClass(str, Enum):
    METROPOLITAN = "METROPOLITAN"
    REGIONAL = "REGIONAL"
    REMOTE = "REMOTE"
    RURAL = "RURAL"

class JurisdictionRef(BaseModel):
    """Lightweight jurisdiction reference for FK includes"""
    id: UUID
    name: str
    
    class Config:
        from_attributes = True

class PostcodeReferenceBase(BaseModel):
    postcode: str
    jurisdiction_id: UUID
    area_class: AreaClass

class PostcodeReference(PostcodeReferenceBase):
    id: UUID
    jurisdiction: Optional[JurisdictionRef] = None
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    
    class Config:
        from_attributes = True
