from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RelatedUnit(BaseModel):
    id: UUID
    code: str
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class ElectricDecarbFactorOut(BaseModel):
    id: UUID
    dataset_revision_id: UUID
    factor_type_code: str
    factor_type_name: Optional[str] = None
    jurisdiction_id: UUID
    jurisdiction_name: Optional[str] = None
    region_id: Optional[UUID] = None
    region_name: Optional[str] = None
    unit_id: Optional[UUID] = None
    unit: Optional[RelatedUnit] = None
    year: int
    value: Optional[float] = None
    value_qualifier: Optional[str] = None

    class Config:
        from_attributes = True


class ElectricDecarbFactorUpdate(BaseModel):
    value: Optional[float] = None
    value_qualifier: Optional[str] = None


class DecarbBulkCreate(BaseModel):
    dataset_revision_id: UUID
    factor_type_code: str
    jurisdiction_id: UUID
    region_id: Optional[UUID] = None
    year_from: int
    year_to: int
