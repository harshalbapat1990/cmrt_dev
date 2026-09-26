from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as _sa_select

from core.security import get_current_principal, Principal
from core.session import get_session
from core.rbac import require_stage_access
from core.authorization_policy import  AccessLevel
# from core.rbac import get_effective_role_names, SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR
from crud.audit_logs import write_audit_event
from models.project_options import ProjectOption as _ProjectOption
from models.project_reporting_submission import ProjectReportingSubmission as _PeriodModel
from pydantic import BaseModel
from crud.activity_data import (
    create_activity_data,
    get_activity_data,
    list_activity_data,
    update_activity_data,
    delete_activity_data,
    bulk_upsert_activity_data,
    enrich_with_emissions,
    seed_from_design,
    OPS_TABLE_KEYS,
)
from crud.project import get_project
from crud.project_stage_instances import get_project_stage_instance, list_project_stage_instances
from crud.project_reporting_submission import get_construction_period, list_construction_periods
from models.project_stage_instances import ProjectStage
from schemas.activity_data import ActivityDataCreate, ActivityDataOut, ActivityDataUpdate
from services.emissions_calculator import calculate_and_store
from services.auto_substitution_mitigation import (
    AUTO_SUBSTITUTION_TABLE_KEYS,
    delete_linked_auto_substitution_mitigation,
    preclean_linked_auto_substitution_mitigations,
    sync_auto_substitution_for_source_row,
)
from services.auto_electricity_mitigation import (
    AUTO_ELECTRICITY_TABLE_KEYS,
    _mitigation_id_from_extra,
    preclean_linked_auto_electricity_mitigations,
    resync_auto_electricity_bucket_after_delete,
    sync_auto_electricity_after_row_change,
    sync_auto_electricity_for_table,
)

router = APIRouter(prefix="/api/activity-data", tags=["activity-data"])


class SeedFromDesignRequest(BaseModel):
    design_option_id: UUID
    construction_stage_instance_id: UUID
    period_ids: List[UUID]

# EDITOR_ROLES = {SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR}

_SKIP_EF_FIELDS = frozenset({
    "id",
    "quantity",
    "unit_id",
    "emissions_tco2e",
    "market_based_tco2e",
    "location_based_tco2e",
    "total_emissions_tco2e",
    "carbon_credits",
})


def _activity_audit_snapshot(obj) -> dict:
    snap: dict = {}
    for field in ("lifecycle_module_code", "dataset_revision_id"):
        v = getattr(obj, field, None)
        if v is not None:
            snap[field] = str(v)
    ef = getattr(obj, "extra_fields", None) or {}
    has_quantity_variant = any(
        k.startswith("quantity_") for k in ef if k not in _SKIP_EF_FIELDS
    )
    if not has_quantity_variant:
        v = getattr(obj, "quantity", None)
        if v is not None:
            snap["quantity"] = str(v)
    for k, v in ef.items():
        if k not in _SKIP_EF_FIELDS:
            snap[f"ef:{k}"] = v
    nk = getattr(obj, "metric_natural_key", None)
    if nk:
        snap["metric_natural_key"] = dict(nk)
    return snap


async def _build_activity_metadata(
    db: AsyncSession,
    project_id: UUID,
    stage_instance,
    ui_table_key: str,
    project_option_id: Optional[UUID] = None,
    submission_period_id: Optional[UUID] = None,
) -> dict:
    meta: dict = {
        "project_id": str(project_id),
        "stage": getattr(stage_instance.stage, "value", stage_instance.stage),
        "stage_instance_id": str(stage_instance.id),
        "ui_table_key": ui_table_key,
    }
    if project_option_id:
        opt_row = (await db.execute(
            _sa_select(_ProjectOption.label, _ProjectOption.report_number).where(_ProjectOption.id == project_option_id)
        )).one_or_none()
        if opt_row:
            meta["option_label"] = opt_row.label
            meta["report_number"] = str(opt_row.report_number)
        meta["project_option_id"] = str(project_option_id)
    if submission_period_id:
        plabel = (await db.execute(
            _sa_select(_PeriodModel.period_label).where(_PeriodModel.id == submission_period_id)
        )).scalar_one_or_none()
        if plabel:
            meta["period_label"] = plabel
    return meta


def _assert_stage_not_locked(stage_instance, submission_period_id=None) -> None:
    if stage_instance and stage_instance.approval_status == "final_approved":
        if submission_period_id is not None:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This stage is final-approved and cannot be edited.",
        )


# async def _require_editor_role(db: AsyncSession, principal: Principal, project_id: UUID) -> None:
#     roles = await get_effective_role_names(db, principal.user_id, project_id)
#     if not roles.intersection(EDITOR_ROLES):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You do not have permission to modify activity data for this project.",
#         )


async def _assert_period_editable(db: AsyncSession, submission_period_id: Optional[UUID]) -> None:
    if submission_period_id is None:
        return
    period = await get_construction_period(db, submission_period_id)
    if period and period.status not in ("in_progress", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This submission period is locked (status: {period.status}) and cannot be edited.",
        )


@router.post("", response_model=ActivityDataOut, status_code=status.HTTP_201_CREATED)
async def create_row(
    payload: ActivityDataCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    stage_instance = await get_project_stage_instance(db, payload.project_stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.EDIT
    )
    _assert_stage_not_locked(stage_instance, payload.submission_period_id)
    await _assert_period_editable(db, payload.submission_period_id)

    obj = await create_activity_data(db, payload)
    await calculate_and_store(db, obj)
    if payload.ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
        proj = await get_project(db, payload.project_id)
        await sync_auto_substitution_for_source_row(db, obj, stage_instance, project=proj)
    if payload.ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS and payload.project_mitigation_id is None:
        proj = await get_project(db, payload.project_id)
        await sync_auto_electricity_after_row_change(db, obj, stage_instance, project=proj)
    if stage_instance.stage == ProjectStage.DESIGN and payload.ui_table_key in OPS_TABLE_KEYS and payload.project_option_id:
        await _auto_sync_to_construction(db, stage_instance, payload.project_option_id)
    _meta = await _build_activity_metadata(
        db, payload.project_id, stage_instance, payload.ui_table_key,
        project_option_id=payload.project_option_id,
        submission_period_id=payload.submission_period_id,
    )
    _snap = _activity_audit_snapshot(obj)
    if _snap:
        _meta["new_values"] = _snap
    await write_audit_event(
        db,
        entity_type="activity_data",
        entity_id=obj.id,
        action="CREATE",
        entity_name=payload.ui_table_key,
        metadata=_meta,
    )
    await db.commit()
    await db.refresh(obj)
    return await enrich_with_emissions(db, obj)


@router.get("", response_model=List[ActivityDataOut])
async def list_rows(
    stage_instance_id: UUID = Query(..., description="Filter by project stage instance ID"),
    ui_table_key: str = Query(..., description="Table key: asset | component | componentRepl | refurbishment | opEnergy | construction"),
    project_option_id: Optional[UUID] = Query(None),
    submission_period_id: Optional[UUID] = Query(None),
    project_mitigation_id: Optional[UUID] = Query(
        None,
        description="When set, only rows linked to this project_mitigations.id (mitigation activity rows).",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    stage_instance = await get_project_stage_instance(db, stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project stage instance not found.")
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance_id,
        AccessLevel.VIEW
    )
    list_kwargs = {
        "project_option_id": project_option_id,
        "skip": skip,
        "limit": limit,
    }
    if submission_period_id is not None:
        list_kwargs["submission_period_id"] = submission_period_id
    if project_mitigation_id is not None:
        list_kwargs["project_mitigation_id"] = project_mitigation_id

    rows = await list_activity_data(
        db, stage_instance_id, ui_table_key, **list_kwargs
    )
    return [await enrich_with_emissions(db, r) for r in rows]


@router.get("/{row_id}", response_model=ActivityDataOut)
async def get_row(
    row_id: UUID, 
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session)
):
    obj = await get_activity_data(db, row_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Activity data row not found."
        )
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.project_stage_instance_id,
        AccessLevel.VIEW
    )
    return await enrich_with_emissions(db, obj)


@router.patch("/{row_id}", response_model=ActivityDataOut)
async def update_row(
    row_id: UUID,
    payload: ActivityDataUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_activity_data(db, row_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity data row not found.")
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.project_stage_instance_id,
        AccessLevel.EDIT
    )
    stage_instance = await get_project_stage_instance(db, obj.project_stage_instance_id)
    submission_period_id = getattr(obj, "submission_period_id", None)
    _assert_stage_not_locked(stage_instance, submission_period_id)
    await _assert_period_editable(db, submission_period_id)

    _snap_before = _activity_audit_snapshot(obj)
    updated = await update_activity_data(db, row_id, payload)
    await calculate_and_store(db, updated)
    if updated.ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
        proj = await get_project(db, updated.project_id)
        await sync_auto_substitution_for_source_row(db, updated, stage_instance, project=proj)
        await db.refresh(updated)
    if updated.ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS and getattr(updated, "project_mitigation_id", None) is None:
        proj = await get_project(db, updated.project_id)
        await sync_auto_electricity_after_row_change(db, updated, stage_instance, project=proj)
        await db.refresh(updated)
    if stage_instance.stage == ProjectStage.DESIGN and obj.ui_table_key in OPS_TABLE_KEYS and obj.project_option_id:
        await _auto_sync_to_construction(db, stage_instance, obj.project_option_id)
    _snap_after = _activity_audit_snapshot(updated)
    _meta = await _build_activity_metadata(
        db, obj.project_id, stage_instance, obj.ui_table_key,
        project_option_id=obj.project_option_id,
        submission_period_id=submission_period_id,
    )
    _changes = {
        k: {"before": _snap_before.get(k), "after": _snap_after.get(k)}
        for k in set(_snap_before) | set(_snap_after)
        if _snap_before.get(k) != _snap_after.get(k)
    }
    if _snap_after:
        _meta["new_values"] = _snap_after
    if _changes:
        _meta["changes"] = _changes
    await write_audit_event(
        db,
        entity_type="activity_data",
        entity_id=row_id,
        action="UPDATE",
        entity_name=obj.ui_table_key,
        metadata=_meta,
    )
    await db.commit()
    await db.refresh(updated)
    return await enrich_with_emissions(db, updated)


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    row_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_activity_data(db, row_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity data row not found.")
    await require_stage_access(
        db,
        principal,
        obj.project_id,
        obj.project_stage_instance_id,
        AccessLevel.EDIT
    )
    stage_instance = await get_project_stage_instance(db, obj.project_stage_instance_id)
    submission_period_id = getattr(obj, "submission_period_id", None)
    _assert_stage_not_locked(stage_instance, submission_period_id)
    await _assert_period_editable(db, submission_period_id)

    if obj.ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
        await delete_linked_auto_substitution_mitigation(db, obj)

    elec_table_key = obj.ui_table_key if obj.ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS else None
    elec_opt_id = obj.project_option_id
    elec_period_id = submission_period_id
    elec_linked_mid = (
        _mitigation_id_from_extra(getattr(obj, "extra_fields", None))
        if elec_table_key and getattr(obj, "project_mitigation_id", None) is None
        else None
    )

    # Capture sync info before deletion
    is_design_ops = stage_instance.stage == ProjectStage.DESIGN and obj.ui_table_key in OPS_TABLE_KEYS and obj.project_option_id
    design_option_id_for_sync = obj.project_option_id if is_design_ops else None

    _snap = _activity_audit_snapshot(obj)
    deleted = await delete_activity_data(db, row_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity data row not found.")
    if is_design_ops:
        await _auto_sync_to_construction(db, stage_instance, design_option_id_for_sync)
    if elec_table_key and getattr(obj, "project_mitigation_id", None) is None:
        proj = await get_project(db, obj.project_id)
        await resync_auto_electricity_bucket_after_delete(
            db,
            stage_instance,
            elec_table_key,
            elec_opt_id,
            elec_period_id,
            project=proj,
            known_mitigation_id=elec_linked_mid,
        )
    _meta = await _build_activity_metadata(
        db, obj.project_id, stage_instance, obj.ui_table_key,
        project_option_id=obj.project_option_id,
        submission_period_id=submission_period_id,
    )
    if _snap:
        _meta["old_values"] = _snap
    await write_audit_event(
        db,
        entity_type="activity_data",
        entity_id=row_id,
        action="DELETE",
        entity_name=obj.ui_table_key,
        metadata=_meta,
    )
    await db.commit()


async def _auto_sync_to_construction(
    db: AsyncSession,
    design_stage_instance,
    design_option_id: UUID,
) -> None:
    """Propagate saved Design OPS rows to all editable Construction periods."""
    all_stages = await list_project_stage_instances(db, project_id=design_stage_instance.project_id)
    construction_si = next(
        (s for s in all_stages if s.stage == ProjectStage.CONSTRUCTION), None
    )
    if not construction_si:
        return
    all_periods = await list_construction_periods(db, construction_si.id)
    period_ids = [p.id for p in all_periods]
    if not period_ids:
        return
    # seed_from_design internally filters to in_progress/rejected only
    await seed_from_design(db, design_option_id, construction_si.id, period_ids)


@router.post("/bulk", response_model=List[ActivityDataOut], status_code=status.HTTP_201_CREATED)
async def bulk_upsert_rows(
    stage_instance_id: UUID = Query(...),
    ui_table_key: str = Query(...),
    payload: List[ActivityDataCreate] = ...,
    project_option_id: Optional[UUID] = Query(
        None,
        description="When bulk payload is empty, scope source-row replace and electricity auto-sync to this option.",
    ),
    submission_period_id: Optional[UUID] = Query(
        None,
        description="When bulk payload is empty, scope source-row replace and electricity auto-sync to this period.",
    ),
    project_mitigation_id: Optional[UUID] = Query(
        None,
        description="Scope delete/replace to this mitigation (activity_data.project_mitigation_id).",
    ),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    stage_instance = await get_project_stage_instance(db, stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage instance not found.")
    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.EDIT
    )
    any_period_id = next((r.submission_period_id for r in payload if r.submission_period_id), None)
    _assert_stage_not_locked(stage_instance, any_period_id)
    await _assert_period_editable(db, any_period_id)

    if project_mitigation_id is None and ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
        await preclean_linked_auto_substitution_mitigations(db, stage_instance_id, ui_table_key, payload)
    if project_mitigation_id is None and ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS:
        await preclean_linked_auto_electricity_mitigations(db, stage_instance_id, ui_table_key, payload)

    rows = await bulk_upsert_activity_data(
        #db, stage_instance_id, ui_table_key, payload, project_mitigation_id=project_mitigation_id
        db,
        stage_instance_id,
        ui_table_key,
        payload,
        project_mitigation_id=project_mitigation_id,
        replace_option_id=project_option_id,
        replace_submission_period_id=submission_period_id,
    )
    for row in rows:
        await calculate_and_store(db, row)

    design_option_id: Optional[UUID] = None
    # Auto-sync to Construction when Design OPS data is saved
    if stage_instance.stage == ProjectStage.DESIGN and ui_table_key in OPS_TABLE_KEYS and payload:
        design_option_id = next(
            (r.project_option_id for r in payload if r.project_option_id), None
        )
    if design_option_id:
        await _auto_sync_to_construction(db, stage_instance, design_option_id)

    if project_mitigation_id is None and ui_table_key in AUTO_SUBSTITUTION_TABLE_KEYS:
        proj = await get_project(db, stage_instance.project_id)
        for row in rows:
            await sync_auto_substitution_for_source_row(db, row, stage_instance, project=proj)
            
    if project_mitigation_id is None and ui_table_key in AUTO_ELECTRICITY_TABLE_KEYS:
        proj = await get_project(db, stage_instance.project_id)
        if payload:
            buckets = {(r.project_option_id, r.submission_period_id) for r in payload}
        elif project_option_id is not None:
            buckets = {(project_option_id, submission_period_id)}
        else:
            buckets = set()
        for opt_id, period_id in buckets:
            await sync_auto_electricity_for_table(
                db,
                stage_instance,
                ui_table_key,
                opt_id,
                period_id,
                project=proj,
            )

            
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return [await enrich_with_emissions(db, r) for r in rows]


@router.post("/seed-from-design", status_code=status.HTTP_200_OK)
async def seed_from_design_endpoint(
    payload: SeedFromDesignRequest,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    stage_instance = await get_project_stage_instance(db, payload.construction_stage_instance_id)
    if not stage_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Construction stage instance not found.")

    await require_stage_access(
        db,
        principal,
        stage_instance.project_id,
        stage_instance.id,
        AccessLevel.EDIT
    )
    count = await seed_from_design(
        db,
        payload.design_option_id,
        payload.construction_stage_instance_id,
        payload.period_ids,
    )
    await db.commit()
    return {"seeded": count}