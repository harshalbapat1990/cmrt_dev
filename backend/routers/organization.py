from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.rbac import SUPER_ADMIN, ORG_ADMIN, require_role
from core.security import Principal, get_current_principal, get_optional_principal
from core.session import get_session
from crud.audit_logs import write_audit_event
from schemas.organization import OrganizationOut, OrganizationCreate, OrganizationUpdate, OrganizationTypeEnum
from crud.organization import (
    create_organization, get_organization, list_organizations, update_organization, delete_organization
)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_org(
    payload: OrganizationCreate,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    obj = await create_organization(db, payload)
    await write_audit_event(
        db,
        entity_type="organisation",
        entity_id=obj.id,
        action="CREATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
        metadata={"name": obj.name},
    )
    await db.commit()
    return obj

@router.get("", response_model=List[OrganizationOut])
async def get_orgs(
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    organization_type: Optional[str] = Query(None, description="Filter by organization type: DESIGNERS or CONTRACTORS"),
    q: Optional[str] = Query(None, description="Search by name"),
    _: Optional[Principal] = Depends(get_optional_principal),
    db: AsyncSession = Depends(get_session),
):
    org_type_value = None
    if organization_type:
        from schemas.organization import OrganizationTypeEnum
        try:
            org_type_value = OrganizationTypeEnum(organization_type).value
        except ValueError:
            org_type_value = None
    rows = await list_organizations(db, skip, limit, is_active, org_type_value, q)
    return rows

@router.get("/{id:uuid}", response_model=OrganizationOut)
async def get_org_by_id(
    id: UUID,
    _: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_organization(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return obj

@router.patch("/{id:uuid}", response_model=OrganizationOut)
async def patch_org(
    id: UUID,
    payload: OrganizationUpdate,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN, ORG_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    obj = await get_organization(db, id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    obj = await update_organization(db, obj, payload)
    await write_audit_event(
        db,
        entity_type="organisation",
        entity_id=id,
        action="UPDATE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
    )
    await db.commit()
    return obj


@router.delete("/{id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org(
    id: UUID,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_role(SUPER_ADMIN)),
    db: AsyncSession = Depends(get_session),
):
    ok = await delete_organization(db, id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    await write_audit_event(
        db,
        entity_type="organisation",
        entity_id=id,
        action="DELETE",
        performed_by=principal.user_id,
        performed_by_org=principal.organization_id,
    )
    await db.commit()
    return None