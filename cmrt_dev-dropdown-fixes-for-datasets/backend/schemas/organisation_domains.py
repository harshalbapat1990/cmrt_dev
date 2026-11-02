from pydantic import BaseModel, UUID4
from typing import Optional

class OrganizationDomainBase(BaseModel):
    organization_id: UUID4
    domain: str
    is_active: Optional[bool] = True

class OrganizationDomainCreate(OrganizationDomainBase):
    pass

class OrganizationDomainUpdate(OrganizationDomainBase):
    pass

class OrganizationDomainInDB(OrganizationDomainBase):
    id: UUID4
    created_on: Optional[str]
    updated_on: Optional[str]

class OrganizationDomainOut(OrganizationDomainInDB):
    pass
