from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DefaultTransportDistanceBase(BaseModel):
    dataset_revision_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    emissions_category_id: Optional[UUID] = None
    jurisdiction_id: UUID
    truck_distance: Optional[Decimal] = None
    rail_distance: Optional[Decimal] = None
    sea_distance: Optional[Decimal] = None
    distance_unit_id: Optional[UUID] = None
    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    sea_transport_mode: Optional[str] = None
    source: Optional[str] = None
    grade_applicability: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DefaultTransportDistanceCreate(DefaultTransportDistanceBase):
    pass


class DefaultTransportDistanceUpdate(BaseModel):
    material_id: Optional[UUID] = None
    emissions_category_id: Optional[UUID] = None
    jurisdiction_id: Optional[UUID] = None
    truck_distance: Optional[Decimal] = None
    rail_distance: Optional[Decimal] = None
    sea_distance: Optional[Decimal] = None
    distance_unit_id: Optional[UUID] = None
    truck_transport_mode: Optional[str] = None
    rail_transport_mode: Optional[str] = None
    sea_transport_mode: Optional[str] = None
    source: Optional[str] = None
    grade_applicability: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class DefaultTransportDistanceOut(DefaultTransportDistanceBase):
    id: UUID
    is_active: bool = True

    class Config:
        from_attributes = True


class DefaultTransportDistanceWithNamesOut(DefaultTransportDistanceOut):
    material_name: Optional[str] = None
    emissions_category_name: Optional[str] = None
    jurisdiction_name: Optional[str] = None
