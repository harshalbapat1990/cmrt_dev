from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from crud.maintenance_replacement_factors import (
    delete_maintenance_replacement_factor,
    list_maintenance_replacement_factors,
    list_maintenance_replacement_factors_active,
    update_maintenance_replacement_factor,
)
from schemas.maintenance_replacement_factors import (
    MaintenanceReplacementFactorOut,
    MaintenanceReplacementFactorUpdate,
)

from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from models.maintenance_replacement_factors import MaintenanceReplacementFactor
from models.organizations import Organization
from models.jurisdictions import Jurisdiction
from sqlalchemy import select

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(
    prefix="/api/maintenance-replacement-factors",
    tags=["maintenance-replacement-factors"],
)


@router.get("/active", response_model=List[MaintenanceReplacementFactorOut])
async def get_active_maintenance_replacement_factors(
    jurisdiction_name: Optional[str] = Query(None, description="Filter by jurisdiction name (e.g. 'Australia')"),
    use_org_jurisdiction: bool = Query(False),
    current_user: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    if use_org_jurisdiction and current_user.organization_id:
        org_result = await db.execute(
            select(Organization.jurisdiction_id)
            .where(Organization.id == current_user.organization_id)
        )

        org_jurisdiction_id = org_result.scalar_one_or_none()

        if org_jurisdiction_id:
            jurisdiction_name = (
                await db.execute(
                    select(Jurisdiction.name)
                    .where(Jurisdiction.id == org_jurisdiction_id)
                )
            ).scalar_one_or_none()
    return await list_maintenance_replacement_factors_active(db, jurisdiction_name=jurisdiction_name)


@router.get("", response_model=List[MaintenanceReplacementFactorOut])
async def get_maintenance_replacement_factors(
    dataset_revision_id: Optional[UUID] = Query(None, description="Filter by dataset revision"),
    jurisdiction_id: Optional[UUID] = Query(None, description="Filter by jurisdiction"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
):
    return await list_maintenance_replacement_factors(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        skip=skip,
        limit=limit,
    )


@router.put("/{factor_id}", response_model=MaintenanceReplacementFactorOut)
async def update_maintenance_replacement(
    factor_id: UUID,
    body: MaintenanceReplacementFactorUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(MaintenanceReplacementFactor.dataset_revision_id)
        .where(MaintenanceReplacementFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="maintenance_replacement_factors",
    )

    try:
        result = await update_maintenance_replacement_factor(
            db,
            factor_id,
            body.emissions_intensity_tco2e,
            body.default_frequency_years,
            body.source_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Factor not found")
    return result


@router.delete("/{factor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_replacement(
    factor_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    res = await db.execute(
        select(MaintenanceReplacementFactor.dataset_revision_id)
        .where(MaintenanceReplacementFactor.id == factor_id)
    )
    revision_id = res.scalar_one_or_none()
    if revision_id is None:
        raise HTTPException(status_code=404, detail="Factor not found")

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=revision_id,
        dataset_type="maintenance_replacement_factors",
    )

    try:
        ok = await delete_maintenance_replacement_factor(db, factor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Factor not found")
    await db.commit()
    return None

protect_dataset_reads(router)
