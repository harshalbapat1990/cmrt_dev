from datetime import datetime, date
from typing import Any, Optional, List
from uuid import UUID
from enum import Enum
 
from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict


def _au_postcode_to_region(postcode_str: str) -> str | None:
    """Map an Australian postcode string to its NEM/WA/NT grid region."""
    try:
        pc = int(postcode_str.strip())
    except (ValueError, AttributeError):
        return None
    if (1000 <= pc <= 2599) or (2619 <= pc <= 2899) or (2921 <= pc <= 2999):
        return "New South Wales"
    if (200 <= pc <= 299) or (2600 <= pc <= 2618) or (2900 <= pc <= 2920):
        return "Australian Capital Territory"
    if (3000 <= pc <= 3999) or (8000 <= pc <= 8999):
        return "Victoria"
    if (4000 <= pc <= 4999) or (9000 <= pc <= 9999):
        return "Queensland"
    if 5000 <= pc <= 5999:
        return "South Australia"
    if 6000 <= pc <= 6999:
        return "Western Australia"
    if 7000 <= pc <= 7999:
        return "Tasmania"
    if 800 <= pc <= 899:
        return "Northern Territory"
    return None


# Benchmark type schemas (resolved objects)
class BenchmarkMastertypeRef(BaseModel):
    id: UUID
    code: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class BenchmarkTypecastRef(BaseModel):
    id: UUID
    code: str
    name: str
    mastertype_id: UUID
    model_config = ConfigDict(from_attributes=True)


class ProjectClassEnum(str, Enum):
    SMALL = "SMALL"
    LARGE = "LARGE"
    RECURRING = "RECURRING"
 
class ProjectStageEnum(str, Enum):
    BUSINESS_CASE = "BUSINESS_CASE"
    DESIGN = "DESIGN"
    CONSTRUCTION = "CONSTRUCTION"
 
class ReportFrequencyEnum(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BI_MONTHLY = "BI_MONTHLY"
    ANNUAL = "ANNUAL"
 
class OrgRoleEnum(str, Enum):
    PROPONENT = "PROPONENT"
    DESIGNER  = "DESIGNER"
    DELIVERY  = "DELIVERY"
 

 
class StageConfigIn(BaseModel):
    stage: ProjectStageEnum
    enabled: bool = False
    num_reports_required: Optional[int] = Field(default=None, ge=0)
    frequency: Optional[ReportFrequencyEnum] = None
    min_requirements: Optional[dict] = None
 
 
class OrgLinkIn(BaseModel):
    organization_id: Optional[UUID] = None
    org_name: Optional[str] = None  # free-text: uppercased and find-or-created server-side
    role: OrgRoleEnum

    @model_validator(mode="after")
    def _require_id_or_name(self) -> "OrgLinkIn":
        if self.organization_id is None and not (self.org_name or "").strip():
            raise ValueError("Either organization_id or org_name must be provided")
        return self

class ProjectRoleEnum(str, Enum):
    PROJECT_ADMIN = "PROJECT_ADMIN"
    PROJECT_EDITOR = "PROJECT_EDITOR"
    PROJECT_VIEWER = "PROJECT_VIEWER"


class MemberAccessIn(BaseModel):
    user_id: UUID
    role: ProjectRoleEnum


class MemberAccessOut(BaseModel):
    user_id: UUID
    role: ProjectRoleEnum
    user_email: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PostcodeIn(BaseModel):
    postcode: str = Field(min_length=3, max_length=10)


class ReportingBoundaryIn(BaseModel):
    stage_or_activity: str = Field(max_length=100)
    category: str = Field(max_length=500)
    sub_category: str = Field(max_length=500)
    source: Optional[str] = Field(default=None, max_length=500)


class ReportingBoundaryOut(ReportingBoundaryIn):
    id: UUID
    sort_order: int = 0
    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    project_name: str = Field(max_length=200)
    project_type_id: UUID
    project_typecast_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = True
 
    project_class: ProjectClassEnum
 
    simple_carbon_assessment: Optional[bool] = False
    contract_number: Optional[str] = Field(default=None, max_length=100)
    design_contract_number: Optional[str] = Field(default=None, max_length=100)
    construction_contract_number: Optional[str] = Field(default=None, max_length=100)
    program_name: Optional[str] = Field(default=None, max_length=255)
    location_text: Optional[str] = Field(default=None, max_length=255)
 
    construction_start_date: Optional[date] = None
    construction_end_date: Optional[date] = None
    commencement_of_operations: Optional[date] = None
    operational_life_years: Optional[int] = Field(default=None, ge=0)
    project_capex_million: Optional[float] = None
    project_opex: Optional[float] = None
    declared_unit_value: Optional[float] = None
    declared_unit_type: Optional[str] = Field(default=None, max_length=50)
 
    first_submission_month: Optional[date] = None
    maintenance_region: Optional[str] = Field(default=None, max_length=255)
 
    proponent_org_id: UUID
 
    model_config = ConfigDict(from_attributes=True)
 
 
class ProjectCreate(ProjectBase):
    created_by_user_id: UUID
    stage_configs: List[StageConfigIn]
    org_links: List[OrgLinkIn] = []
    postcodes: List[PostcodeIn] = Field(..., min_length=1, max_length=20)
    member_accesses: List[MemberAccessIn] = []
    reporting_boundaries: List[ReportingBoundaryIn] = []
 
 
class ProjectUpdate(BaseModel):
    project_name: Optional[str] = Field(default=None, max_length=200)
    project_type_id: Optional[UUID] = None
    project_typecast_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None
    project_class: Optional[ProjectClassEnum] = None
    simple_carbon_assessment: Optional[bool] = None
    contract_number: Optional[str] = Field(default=None, max_length=100)
    design_contract_number: Optional[str] = Field(default=None, max_length=100)
    construction_contract_number: Optional[str] = Field(default=None, max_length=100)
    program_name: Optional[str] = Field(default=None, max_length=255)
    location_text: Optional[str] = Field(default=None, max_length=255)
 
    construction_start_date: Optional[date] = None
    construction_end_date: Optional[date] = None
    commencement_of_operations: Optional[date] = None
    operational_life_years: Optional[int] = Field(default=None, ge=0)
    project_capex_million: Optional[float] = None
    project_opex: Optional[float] = None
    declared_unit_value: Optional[float] = None
    declared_unit_type: Optional[str] = Field(default=None, max_length=50)
 
    first_submission_month: Optional[date] = None
    maintenance_region: Optional[str] = Field(default=None, max_length=255)
 
    proponent_org_id: Optional[UUID] = None
    last_updated_by_user_id: Optional[UUID] = None
 
    stage_configs: Optional[List[StageConfigIn]] = None
    org_links: Optional[List[OrgLinkIn]] = None
    postcodes: Optional[List[PostcodeIn]] = Field(default=None, min_length=1, max_length=20)
    member_accesses: Optional[List[MemberAccessIn]] = None
    reporting_boundaries: Optional[List[ReportingBoundaryIn]] = None
 

class StageConfigOut(StageConfigIn):
       id: UUID
       created_on: Optional[datetime] = None
       updated_on: Optional[datetime] = None
       model_config = ConfigDict(from_attributes=True)

class OrgLinkOut(OrgLinkIn):
    id: UUID
    organization_name: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class PostcodeOut(PostcodeIn):
    id: UUID
    area_class: str = Field(max_length=50)
    jurisdiction_name: Optional[str] = None
    grid_region: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _extract_jurisdiction_fields(cls, data: Any) -> Any:
        # Only enrich when given an ORM object (not a plain dict)
        if isinstance(data, dict):
            return data
        jur = getattr(data, "jurisdiction", None)
        jur_name: str | None = getattr(jur, "name", None) if jur else None
        pc_str: str | None = getattr(data, "postcode", None)
        if jur_name and "new zealand" in jur_name.lower():
            region: str | None = "New Zealand"
        else:
            region = _au_postcode_to_region(pc_str) if pc_str else None
        return {
            "id": data.id,
            "postcode": pc_str,
            "area_class": getattr(data, "area_class", None),
            "jurisdiction_name": jur_name,
            "grid_region": region,
            "created_on": getattr(data, "created_on", None),
            "updated_on": getattr(data, "updated_on", None),
        }
class StageInstanceOut(BaseModel):
    id: UUID
    project_id: UUID
    stage: str
    sequence: int = 0
    num_reports_required: Optional[int] = None
    frequency: Optional[str] = None
    approval_status: str = "draft"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    technical_approved_at: Optional[datetime] = None
    current_justification: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProjectPartyOut(BaseModel):
    id: UUID
    project_id: UUID
    organization_id: Optional[UUID] = None
    joint_venture_id: Optional[UUID] = None
    role: str
    role_note: Optional[str] = None
    contract_number: Optional[str] = None
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(ProjectBase):
    id: UUID
    created_by_user_id: UUID
    last_updated_by_user_id: Optional[UUID]
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    # Return both IDs and resolved objects
    project_type_name: Optional[str] = None
    project_typecast_name: Optional[str] = None
    # Resolved benchmark objects
    benchmark_mastertype: Optional[BenchmarkMastertypeRef] = None
    benchmark_typecast: Optional[BenchmarkTypecastRef] = None
    proponent_org_name: Optional[str] = None

    stage_configs: Optional[List[StageConfigOut]] = None
    org_links: Optional[List[OrgLinkOut]] = None
    postcodes: Optional[List[PostcodeOut]] = None
    stage_instances: Optional[List[StageInstanceOut]] = None
    project_parties: Optional[List[ProjectPartyOut]] = None
    reporting_boundaries: Optional[List[ReportingBoundaryOut]] = None
    member_accesses: Optional[List[MemberAccessOut]] = None
    has_entries: bool = False

    model_config = ConfigDict(from_attributes=True)

 