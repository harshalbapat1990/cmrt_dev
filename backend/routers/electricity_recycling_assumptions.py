from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from crud.audit_logs import write_audit_event
from crud.jurisdictions import get_jurisdiction_by_name
from crud.electricity_recycling_assumptions import (
    ensure_electricity_recycling_assumptions,
    get_electricity_recycling_assumption,
    list_electricity_recycling_assumptions,
    resolve_metric_code,
    update_electricity_recycling_assumption,
    upsert_electricity_recycling_assumption,
)
from models.electricity_recycling_assumption import ElectricityRecyclingAssumption
from schemas.electricity_recycling_assumptions import (
    ElectricityRecyclingAssumptionOut,
    ElectricityRecyclingAssumptionPage,
    ElectricityRecyclingAssumptionUpdate,
    ElectricityRecyclingAssumptionUpdateResult,
    ElectricityRecyclingAssumptionUpsert,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(
    prefix="/api/electricity-recycling-assumptions",
    tags=["electricity-recycling-assumptions"],
)


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


def _row_to_out(row: ElectricityRecyclingAssumption) -> ElectricityRecyclingAssumptionOut:
    return ElectricityRecyclingAssumptionOut(
        id=row.id,
        dataset_revision_id=row.dataset_revision_id,
        jurisdiction_id=row.jurisdiction_id,
        jurisdiction_name=row.jurisdiction.name if row.jurisdiction else None,
        metric_code=row.metric_code,
        metric_label=row.metric_label,
        default_bau_pct=row.default_bau_pct,
        is_calculated=row.is_calculated,
        display_order=row.display_order,
    )


@router.get("", response_model=ElectricityRecyclingAssumptionPage)
async def get_electricity_recycling_assumptions(
    dataset_revision_id: Optional[UUID] = Query(
        None,
        description="Scope to a specific dataset revision; omit for global rows",
    ),
    jurisdiction_id: Optional[UUID] = Query(
        None,
        description="Filter by jurisdiction UUID; omit for all jurisdictions",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    await ensure_electricity_recycling_assumptions(db, dataset_revision_id)
    await db.commit()

    rows, total = await list_electricity_recycling_assumptions(
        db,
        dataset_revision_id=dataset_revision_id,
        jurisdiction_id=jurisdiction_id,
        skip=skip,
        limit=limit,
    )
    return ElectricityRecyclingAssumptionPage(
        items=[_row_to_out(r) for r in rows],
        total=total,
    )


@router.post("/upsert", response_model=ElectricityRecyclingAssumptionUpdateResult)
async def upsert_electricity_recycling_assumption_row(
    payload: ElectricityRecyclingAssumptionUpsert,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="electricity_recycling_assumptions",
    )
    jur_id = await _resolve_jurisdiction_id(
        db, payload.jurisdiction_id, payload.jurisdiction_name
    )
    try:
        metric_code = resolve_metric_code(payload.metric_code, payload.metric_label)
        updated, recalc = await upsert_electricity_recycling_assumption(
            db,
            payload.dataset_revision_id,
            jur_id,
            metric_code,
            payload.default_bau_pct,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await write_audit_event(
        db,
        entity_type="electricity_recycling_assumptions",
        entity_id=updated.id,
        action="UPDATE",
        field_name="default_bau_pct",
        new_value=str(payload.default_bau_pct),
    )
    await db.commit()
    await db.refresh(updated)
    return ElectricityRecyclingAssumptionUpdateResult(
        row=_row_to_out(updated),
        recalculated_rows=[_row_to_out(r) for r in recalc],
    )


@router.patch("/{row_id}", response_model=ElectricityRecyclingAssumptionUpdateResult)
async def patch_electricity_recycling_assumption(
    row_id: UUID,
    payload: ElectricityRecyclingAssumptionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_electricity_recycling_assumption(db, row_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Electricity and recycling assumption row not found",
        )

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="electricity_recycling_assumptions",
    )

    try:
        updated, recalc = await update_electricity_recycling_assumption(
            db, obj, payload.default_bau_pct
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await write_audit_event(
        db,
        entity_type="electricity_recycling_assumptions",
        entity_id=updated.id,
        action="UPDATE",
        field_name="default_bau_pct",
        new_value=str(payload.default_bau_pct),
    )
    await db.commit()
    await db.refresh(updated)
    return ElectricityRecyclingAssumptionUpdateResult(
        row=_row_to_out(updated),
        recalculated_rows=[_row_to_out(r) for r in recalc],
    )

protect_dataset_reads(router)
