from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


PartnerType = Literal["DESIGNERS", "CONTRACTORS"]
SuggestionStatus = Literal["pending", "approved", "rejected"]


def normalize_partner_name(name: str) -> str:
    return " ".join(name.split()).casefold().upper()


class PartnerOrganizationOut(BaseModel):
    id: UUID
    name: str
    partner_type: PartnerType
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PartnerOrganizationSuggestionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    partner_type: PartnerType

    @field_validator("name")
    @classmethod
    def normalize_spaces(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Partner name cannot be blank")
        return value


class PartnerOrganizationSuggestionOut(BaseModel):
    id: UUID
    name: str
    partner_type: PartnerType
    status: SuggestionStatus
    created_at: datetime
    submitted_by_user_id: UUID
    partner_organization_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PartnerOrganizationSuggestionReview(BaseModel):
    decision: Literal["approved", "rejected"]
