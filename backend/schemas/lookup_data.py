
# app/schemas/lookup.py
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# --------- category ----------
class EmissionsCategoryOut(BaseModel):
    id: UUID
    name: str
    is_active: Optional[bool] = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

# --------- BGM-filtered lookups ----------
class BgmItemOut(BaseModel):
    """Lightweight {id, name} used for BGM-grade-filtered category/subcategory responses."""
    id: UUID
    name: str

class BgmSourceOut(BaseModel):
    """BGM emissions_source string returned as {id, name} where id == name (the raw source text)."""
    id: str
    name: str

# --------- sub-category ----------
class EmissionsSubCategoryOut(BaseModel):
    id: UUID
    name: str
    emissions_category_id: Optional[UUID] = None
    emissions_category_name: Optional[str] = None
    is_active: Optional[bool] = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

# --------- unit (from units table; code is exposed as name) ----------
class UnitOut(BaseModel):
    id: UUID
    name: Optional[str] = None  # populated from units.code
    is_active: Optional[bool] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

# backward-compat alias
MeasurementUnitOut = UnitOut


class UnitOptionOut(BaseModel):
    id: UUID
    name: str
    label: Optional[str] = None
    is_canonical: bool = True
    to_canonical_factor: Optional[Decimal] = None
    canonical_unit_id: Optional[UUID] = None
    canonical_unit_code: Optional[str] = None

# --------- emission source ----------
class EmissionSourceOut(BaseModel):
    id: UUID
    name: str
    emissions_sub_category_id: Optional[UUID] = None
    emissions_sub_category_name: Optional[str] = None
    emissions_category_id: Optional[UUID] = None
    emissions_category_name: Optional[str] = None
    measurement_unit_id: Optional[UUID] = None
    measurement_unit_name: Optional[str] = None
    is_active: Optional[bool] = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

# --------- emission factor ----------
class EmissionFactorOut(BaseModel):
    id: UUID
    emission_source_id: UUID
    emission_source_name: str
    measurement_unit_id: UUID
    measurement_unit_name: Optional[str] = None
    is_active: Optional[bool] = True
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

# --------- emission factor value ----------
class EmissionFactorValueOut(BaseModel):
    id: UUID
    emission_factor_id: UUID
    stage_code: str
    gwp_kgco2e_per_unit: Decimal
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None

class EmissionFactorWithValuesOut(BaseModel):
    factor: EmissionFactorOut
    values: List[EmissionFactorValueOut]
