from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DirectSubstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_revision_id: UUID
    jurisdiction_id: UUID
    jurisdiction_name: str | None = None
    user_emissions_source: str
    user_unit: str
    bau_equivalent_emission_source: str
    bau_equivalent_unit: str
    bau_quantity_per_user_unit: Decimal
    display_order: int


class DirectSubstitutionPage(BaseModel):
    items: list[DirectSubstitutionOut] = Field(default_factory=list)
    total: int = 0


class DirectSubstitutionCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    dataset_revision_id: UUID
    jurisdiction_id: Optional[UUID] = None
    jurisdiction_name: Optional[str] = None
    user_emissions_source: str
    user_unit: str
    bau_equivalent_emission_source: str
    bau_equivalent_unit: str
    bau_quantity_per_user_unit: Decimal
    display_order: int = 0

    @model_validator(mode='after')
    def require_jurisdiction_ref(self):
        has_id = self.jurisdiction_id is not None
        has_name = bool(self.jurisdiction_name and self.jurisdiction_name.strip())
        if not has_id and not has_name:
            raise ValueError('Provide jurisdiction_id or jurisdiction_name')
        return self


class DirectSubstitutionUpdate(BaseModel):
    model_config = ConfigDict(extra='ignore')

    jurisdiction_id: Optional[UUID] = None
    jurisdiction_name: Optional[str] = None
    user_emissions_source: Optional[str] = None
    user_unit: Optional[str] = None
    bau_equivalent_emission_source: Optional[str] = None
    bau_equivalent_unit: Optional[str] = None
    bau_quantity_per_user_unit: Optional[Decimal] = None
    display_order: Optional[int] = None


class DirectSubstitutionUpsert(BaseModel):
    """Create or update by natural key (jurisdiction + source/unit pairs); optionally dedupe extras."""

    model_config = ConfigDict(extra='ignore')

    dataset_revision_id: UUID
    jurisdiction_id: Optional[UUID] = None
    jurisdiction_name: Optional[str] = None
    user_emissions_source: str
    user_unit: str
    bau_equivalent_emission_source: str
    bau_equivalent_unit: str
    bau_quantity_per_user_unit: Decimal
    display_order: Optional[int] = None

    @model_validator(mode='after')
    def require_jurisdiction_ref(self):
        has_id = self.jurisdiction_id is not None
        has_name = bool(self.jurisdiction_name and self.jurisdiction_name.strip())
        if not has_id and not has_name:
            raise ValueError('Provide jurisdiction_id or jurisdiction_name')
        return self
