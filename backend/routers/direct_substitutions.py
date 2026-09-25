from typing import Optional, TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.jurisdictions import get_jurisdiction_by_name
from crud.direct_substitutions import (
    create_direct_substitution,
    get_direct_substitution,
    list_direct_substitutions,
    update_direct_substitution,
    upsert_direct_substitution,
)
from schemas.direct_substitutions import (
    DirectSubstitutionCreate,
    DirectSubstitutionOut,
    DirectSubstitutionPage,
    DirectSubstitutionUpdate,
    DirectSubstitutionUpsert,
)

if TYPE_CHECKING:
    from models.direct_substitution_factors import DirectSubstitutionFactor

router = APIRouter(prefix="/api/direct-substitutions", tags=["direct-substitutions"])


async def _resolve_jurisdiction_id(
    db: AsyncSession,
    jurisdiction_id: Optional[UUID],
    jurisdiction_name: Optional[str],
) -> UUID:
    if jurisdiction_id is not None:
        return jurisdiction_id
    name = (jurisdiction_name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jurisdiction_id or jurisdiction_name is required",
        )
    jur = await get_jurisdiction_by_name(db, name)
    if jur is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown jurisdiction: {name!r}",
        )
    return jur.id


def _row_to_out(r: "DirectSubstitutionFactor") -> DirectSubstitutionOut:
    return DirectSubstitutionOut(
        id=r.id,
        jurisdiction_id=r.jurisdiction_id,
        jurisdiction_name=r.jurisdiction.name if r.jurisdiction else None,
        user_emissions_source=r.user_emissions_source,
        user_unit=r.user_unit,
        bau_equivalent_emission_source=r.bau_equivalent_emission_source,
        bau_equivalent_unit=r.bau_equivalent_unit,
        bau_quantity_per_user_unit=r.bau_quantity_per_user_unit,
        display_order=r.display_order,
    )


@router.post("", response_model=DirectSubstitutionOut, status_code=status.HTTP_201_CREATED)
async def create_direct_substitution_row(
    payload: DirectSubstitutionCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="direct_substitutions",
    )
    jur_id = await _resolve_jurisdiction_id(
        db, payload.jurisdiction_id, payload.jurisdiction_name
    )
    obj = await create_direct_substitution(db, payload, jur_id)
    await db.commit()
    await db.refresh(obj)
    return _row_to_out(obj)


@router.post("/upsert", response_model=DirectSubstitutionOut)
async def upsert_direct_substitution_row(
    payload: DirectSubstitutionUpsert,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="direct_substitutions",
    )
    jur_id = await _resolve_jurisdiction_id(
        db, payload.jurisdiction_id, payload.jurisdiction_name
    )
    obj = await upsert_direct_substitution(db, payload, jur_id)
    await db.commit()
    await db.refresh(obj)
    return _row_to_out(obj)


@router.patch("/{factor_id}", response_model=DirectSubstitutionOut)
async def patch_direct_substitution_row(
    factor_id: UUID,
    payload: DirectSubstitutionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=None,
        dataset_type="direct_substitutions",
    )
    obj = await get_direct_substitution(db, factor_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Row not found")
    patch_data = payload.model_dump(exclude_unset=True)
    jname = patch_data.pop("jurisdiction_name", None)
    if jname is not None:
        ns = str(jname).strip()
        if ns:
            patch_data["jurisdiction_id"] = await _resolve_jurisdiction_id(
                db, patch_data.get("jurisdiction_id"), ns
            )
    payload_orm = DirectSubstitutionUpdate(**patch_data)
    obj = await update_direct_substitution(db, obj, payload_orm)
    await db.commit()
    await db.refresh(obj)
    return _row_to_out(obj)


@router.get("", response_model=DirectSubstitutionPage)
async def get_direct_substitutions(
    jurisdiction_id: Optional[UUID] = Query(
        None,
        description="Filter by jurisdiction UUID; omit for all jurisdictions",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    rows, total = await list_direct_substitutions(
        db,
        jurisdiction_id=jurisdiction_id,
        skip=skip,
        limit=limit,
    )
    items = [_row_to_out(r) for r in rows]
    return DirectSubstitutionPage(items=items, total=total)
