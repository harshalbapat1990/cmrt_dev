from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CarbonValueOut(BaseModel):
    id: UUID
    dataset_revision_id: Optional[UUID] = None
    jurisdiction_id: UUID
    jurisdiction_name: Optional[str] = None
    range_code: str
    range_name: Optional[str] = None
    year: int
    value: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class CarbonValueUpdate(BaseModel):
    value: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None


class CarbonValueBulkCreate(BaseModel):
    dataset_revision_id: UUID
    jurisdiction_id: UUID
    range_code: str
    year_from: int
    year_to: int
