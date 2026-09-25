from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ElectricityRecyclingAssumptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_revision_id: UUID | None = None
    jurisdiction_id: UUID
    jurisdiction_name: str | None = None
    metric_code: str
    metric_label: str
    default_bau_pct: Decimal
    is_calculated: bool
    display_order: int


class ElectricityRecyclingAssumptionPage(BaseModel):
    items: list[ElectricityRecyclingAssumptionOut] = Field(default_factory=list)
    total: int = 0


class ElectricityRecyclingAssumptionUpdate(BaseModel):
    default_bau_pct: Decimal


class ElectricityRecyclingAssumptionUpdateResult(BaseModel):
    row: ElectricityRecyclingAssumptionOut
    recalculated_rows: list[ElectricityRecyclingAssumptionOut] = Field(default_factory=list)


class ElectricityRecyclingAssumptionUpsert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_revision_id: UUID
    jurisdiction_id: Optional[UUID] = None
    jurisdiction_name: Optional[str] = None
    metric_code: Optional[str] = None
    metric_label: Optional[str] = None
    default_bau_pct: Decimal

    @model_validator(mode="after")
    def require_refs(self):
        has_jur_id = self.jurisdiction_id is not None
        has_jur_name = bool(self.jurisdiction_name and self.jurisdiction_name.strip())
        if not has_jur_id and not has_jur_name:
            raise ValueError("Provide jurisdiction_id or jurisdiction_name")

        has_code = bool(self.metric_code and self.metric_code.strip())
        has_label = bool(self.metric_label and self.metric_label.strip())
        if not has_code and not has_label:
            raise ValueError("Provide metric_code or metric_label")
        return self
