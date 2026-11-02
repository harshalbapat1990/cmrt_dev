from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MaterialRecycledContentBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    recycled_from_material_id: Optional[UUID] = None
    percent: Optional[Decimal] = None        # stored as fraction 0-1
    jurisdiction_id: Optional[UUID] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class MaterialRecycledContentCreate(MaterialRecycledContentBase):
    pass


class MaterialRecycledContentUpdate(BaseModel):
    material_id: Optional[UUID] = None
    recycled_from_material_id: Optional[UUID] = None
    percent: Optional[Decimal] = None
    jurisdiction_id: Optional[UUID] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class MaterialRecycledContentOut(MaterialRecycledContentBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True


class MaterialRecycledContentWithNamesOut(MaterialRecycledContentOut):
    material_name: Optional[str] = None
    jurisdiction_name: Optional[str] = None
