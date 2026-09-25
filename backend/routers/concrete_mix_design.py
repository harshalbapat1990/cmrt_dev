"""FastAPI router for the BAU concrete mix designs dataset."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.audit_logs import write_audit_event
from crud.concrete_mix_design import (
    ensure_assumptions,
    ensure_mix_designs,
    get_mix_design,
    recompute_calculated_rows,
    update_assumptions,
    update_mix_design,
)
from models.concrete_mix_design import (
    CALCULATED_COMPONENT_CODES,
    TOTAL_CEMENTITIOUS_CODE,
)
from schemas.concrete_mix_design import (
    ConcreteMixAssumptionOut,
    ConcreteMixAssumptionsUpdateResult,
    ConcreteMixAssumptionUpdate,
    ConcreteMixDesignBundle,
    ConcreteMixDesignOut,
    ConcreteMixDesignUpdate,
    ConcreteMixDesignUpdateResult,
)


router = APIRouter(prefix="/api/concrete-mix-designs", tags=["concrete-mix-designs"])


@router.get("", response_model=ConcreteMixDesignBundle)
async def get_concrete_mix_designs(
    dataset_revision_id: Optional[UUID] = Query(
        None,
        description="Scope to a specific dataset revision; omit for global rows",
    ),
    db: AsyncSession = Depends(get_session),
):
   
    assumptions = await ensure_assumptions(db, dataset_revision_id)
    rows = await ensure_mix_designs(db, dataset_revision_id)
    await db.commit()
    await db.refresh(assumptions)
    return ConcreteMixDesignBundle(
        assumptions=ConcreteMixAssumptionOut.model_validate(assumptions),
        rows=[ConcreteMixDesignOut.model_validate(r) for r in rows],
    )


@router.get("/assumptions", response_model=ConcreteMixAssumptionOut)
async def get_concrete_mix_assumptions(
    dataset_revision_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_session),
):
    obj = await ensure_assumptions(db, dataset_revision_id)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/assumptions", response_model=ConcreteMixAssumptionsUpdateResult)
async def update_concrete_mix_assumptions(
    payload: ConcreteMixAssumptionUpdate,
    dataset_revision_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=dataset_revision_id,
        dataset_type="concrete_mix_designs",
    )
    obj = await ensure_assumptions(db, dataset_revision_id)
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        recalc = await recompute_calculated_rows(db, dataset_revision_id)
        await db.commit()
        await db.refresh(obj)
        return ConcreteMixAssumptionsUpdateResult(
            assumptions=ConcreteMixAssumptionOut.model_validate(obj),
            recalculated_rows=[ConcreteMixDesignOut.model_validate(r) for r in recalc],
        )

    new_obj = await update_assumptions(db, obj, patch)
    await write_audit_event(
        db,
        entity_type="concrete_mix_assumptions",
        entity_id=new_obj.id,
        action="UPDATE",
        field_name=",".join(patch.keys()),
        new_value=str({k: str(v) for k, v in patch.items()}),
    )
    # An assumption change always triggers recomputation of every
    # calculated cell across all eight strengths.
    recalc = await recompute_calculated_rows(db, dataset_revision_id)
    await db.commit()
    await db.refresh(new_obj)
    return ConcreteMixAssumptionsUpdateResult(
        assumptions=ConcreteMixAssumptionOut.model_validate(new_obj),
        recalculated_rows=[ConcreteMixDesignOut.model_validate(r) for r in recalc],
    )


@router.patch("/{record_id}", response_model=ConcreteMixDesignUpdateResult)
async def update_concrete_mix_design_row(
    record_id: UUID,
    payload: ConcreteMixDesignUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_mix_design(db, record_id)
    if not obj or not obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concrete mix design row not found",
        )
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="concrete_mix_designs",
    )
    if obj.component_code in CALCULATED_COMPONENT_CODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{obj.component_label}' is a calculated row and cannot be edited "
                "directly; update 'Total cementitious content' or the assumptions instead"
            ),
        )

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return ConcreteMixDesignUpdateResult(
            row=ConcreteMixDesignOut.model_validate(obj),
            recalculated_rows=[],
        )

    new_obj = await update_mix_design(db, obj, patch)
    await write_audit_event(
        db,
        entity_type="concrete_mix_designs",
        entity_id=new_obj.id,
        action="UPDATE",
        field_name=",".join(patch.keys()),
        new_value=str({k: str(v) for k, v in patch.items()}),
    )
    # Recompute calculated rows when the edited row is the trigger
    # (total_cementitious_content). Other input rows don't affect calc.
    recalc: list = []
    if new_obj.component_code == TOTAL_CEMENTITIOUS_CODE:
        recalc = await recompute_calculated_rows(db, new_obj.dataset_revision_id)
    await db.commit()
    await db.refresh(new_obj)
    return ConcreteMixDesignUpdateResult(
        row=ConcreteMixDesignOut.model_validate(new_obj),
        recalculated_rows=[ConcreteMixDesignOut.model_validate(r) for r in recalc],
    )
