"""
Auto-triggered Substitution mitigations for LARGE-project electricity tables.

When users enter Onsite or Offsite Renewable Electricity in the electricity or
opEnergyElectricity source tables, creates a substitution mitigation with:
  - Adopted leg: consolidated user quantities by (emission_source, year)
  - Replaced leg: total year MWh × ERA default BAU % per source
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.activity_data import bulk_upsert_activity_data, update_activity_data
from crud.dataset_revisions import get_published_dataset_revision
from crud.electricity_recycling_assumptions import load_era_bau_pcts_for_jurisdiction
from crud.project import get_project
from crud.project_dataset_revisions import list_project_dataset_revisions_by_project
from crud.project_mitigations import (
    create_project_mitigation,
    delete_project_mitigation,
    get_project_mitigation,
    update_project_mitigation,
)

# Conversion factors to normalise user-entered quantities to MWh.
# Rows stored with unit_display other than MWh must be converted before summing.
_UNIT_TO_MWH: dict[str, float] = {"kWh": 0.001, "MWh": 1.0, "GWh": 1000.0}
from models.activity_data import ActivityData
from models.project import Project, ProjectClass
from models.project_stage_instances import ProjectStage, ProjectStageInstance
from schemas.activity_data import ActivityDataCreate, ActivityDataUpdate
from services.auto_substitution_mitigation import (
    _resolve_jurisdiction_id,
    mitigation_listing_stage_and_option,
    mitigation_substitution_ui_keys,
    pick_emissions_source_label,
    submission_stage_label,
)

logger = logging.getLogger(__name__)

AUTO_ELECTRICITY_TABLE_KEYS: frozenset[str] = frozenset(
    {"electricity", "opEnergyElectricity"}
)

AUTO_ELECTRICITY_LINK_KEY = "auto_electricity_mitigation_id"

RENEWABLE_SOURCES: frozenset[str] = frozenset(
    {
        "Onsite Renewable Electricity",
        "Offsite Renewable Electricity",
    }
)

ALL_ELECTRICITY_SOURCES: Tuple[str, ...] = (
    "Grid Electricity",
    "Onsite Renewable Electricity",
    "Offsite Renewable Electricity",
)

_MITIGATION_NAMES = {
    "electricity": "Auto Triggered: Electricity - Construction",
    "opEnergyElectricity": "Auto Triggered: Electricity - Operationl"
}


def electricity_lifecycle_meta(ui_table_key: str) -> Optional[Tuple[str, str]]:
    if ui_table_key == "electricity":
        return ("construction", "Construction")
    if ui_table_key == "opEnergyElectricity":
        return ("operations_maintenance", "Operations & Maintenance")
    return None


def _mitigation_id_from_extra(extra: Optional[Dict[str, Any]]) -> Optional[UUID]:
    raw = (extra or {}).get(AUTO_ELECTRICITY_LINK_KEY)
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None


def _parse_electricity_row(row: ActivityData) -> Optional[Tuple[str, int, Decimal]]:
    extra = row.extra_fields or {}
    source = pick_emissions_source_label(extra.get("emission_source")).strip()
    if not source:
        return None

    year_raw = extra.get("year")
    if year_raw is None or year_raw == "":
        return None
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return None

    qty_raw = extra.get("quantity_mwh", row.quantity)
    try:
        qty = Decimal(str(qty_raw))
    except (TypeError, ValueError):
        return None
    if qty <= 0:
        return None

    # Normalise to MWh when the row was stored with a different unit
    unit_display = extra.get("unit_display", "MWh")
    conversion_factor = Decimal(str(_UNIT_TO_MWH.get(unit_display, 1.0)))
    qty = qty * conversion_factor

    return source, year, qty


def _has_renewable_trigger(source_rows: Sequence[ActivityData]) -> bool:
    for row in source_rows:
        parsed = _parse_electricity_row(row)
        if parsed and parsed[0] in RENEWABLE_SOURCES:
            return True
    return False


def year_electricity_totals(source_rows: Sequence[ActivityData]) -> Dict[int, Decimal]:
    """Sum Grid + Onsite + Offsite MWh per year (interim totals for replaced leg)."""
    year_totals: Dict[int, Decimal] = {}
    for row in source_rows:
        parsed = _parse_electricity_row(row)
        if not parsed:
            continue
        _, year, qty = parsed
        year_totals[year] = year_totals.get(year, Decimal("0")) + qty
    return year_totals


def consolidate_adopted_rows(
    source_rows: Sequence[ActivityData],
) -> List[Dict[str, Any]]:
    """Sum MWh by (emission_source, year) for rows with valid quantity."""
    totals: Dict[Tuple[str, int], Decimal] = {}
    for row in source_rows:
        parsed = _parse_electricity_row(row)
        if not parsed:
            continue
        source, year, qty = parsed
        key = (source, year)
        totals[key] = totals.get(key, Decimal("0")) + qty

    out: List[Dict[str, Any]] = []
    for (source, year), qty in sorted(totals.items(), key=lambda x: (x[0][1], x[0][0])):
        out.append(
            {
                "emission_source": source,
                "year": year,
                "quantity_mwh": float(qty),
                "unit_display": "MWh",
            }
        )
    return out


def build_replaced_rows(
    source_rows: Sequence[ActivityData],
    era_bau_pcts: Dict[str, Decimal],
) -> List[Dict[str, Any]]:
    """For each year, replaced MWh = totalYear × ERA BAU % per source."""
    out: List[Dict[str, Any]] = []
    for year, total in sorted(year_electricity_totals(source_rows).items()):
        if total <= 0:
            continue
        for source in ALL_ELECTRICITY_SOURCES:
            pct = era_bau_pcts.get(source, Decimal("0"))
            qty = total * pct
            if qty <= 0:
                continue
            out.append(
                {
                    "emission_source": source,
                    "year": year,
                    "quantity_mwh": float(qty),
                    "unit_display": "MWh",
                }
            )
    return out


async def _resolve_dataset_revision_id(
    db: AsyncSession,
    project_id: UUID,
    source_rows: Sequence[ActivityData],
) -> Optional[UUID]:
    """
    Resolve which electricity_recycling_assumptions revision scopes BAU % lookup.

    The project's selected revision is authoritative; row revisions are only a
    compatibility fallback for projects that have not yet been bound.
    """
    pdrs = await list_project_dataset_revisions_by_project(db, project_id)
    if pdrs:
        return pdrs[0].dataset_revision_id
    for row in source_rows:
        if row.dataset_revision_id is not None:
            return row.dataset_revision_id
    published = await get_published_dataset_revision(db)
    if published is not None:
        return published.id
    return None


async def _load_source_rows(
    db: AsyncSession,
    stage_instance_id: UUID,
    ui_table_key: str,
    project_option_id: Optional[UUID],
    submission_period_id: Optional[UUID],
) -> List[ActivityData]:
    q = select(ActivityData).where(
        ActivityData.project_stage_instance_id == stage_instance_id,
        ActivityData.ui_table_key == ui_table_key,
        ActivityData.project_mitigation_id.is_(None),
    )
    if project_option_id is not None:
        q = q.where(ActivityData.project_option_id == project_option_id)
    else:
        q = q.where(ActivityData.project_option_id.is_(None))
    if submission_period_id is not None:
        q = q.where(ActivityData.submission_period_id == submission_period_id)
    else:
        q = q.where(ActivityData.submission_period_id.is_(None))
    res = await db.execute(q)
    return list(res.scalars().all())


def _bucket_key(
    project_option_id: Optional[UUID],
    submission_period_id: Optional[UUID],
) -> Tuple[Optional[UUID], Optional[UUID]]:
    return project_option_id, submission_period_id


async def _delete_linked_mitigation_if_any(
    db: AsyncSession,
    source_rows: Sequence[ActivityData],
) -> None:
    seen: Set[UUID] = set()
    for row in source_rows:
        mid = _mitigation_id_from_extra(row.extra_fields)
        if mid and mid not in seen:
            seen.add(mid)
            await delete_project_mitigation(db, mid)


async def _clear_links_on_sources(
    db: AsyncSession,
    source_rows: Sequence[ActivityData],
) -> None:
    for row in source_rows:
        if _mitigation_id_from_extra(row.extra_fields):
            ef = dict(row.extra_fields or {})
            ef.pop(AUTO_ELECTRICITY_LINK_KEY, None)
            await update_activity_data(db, row.id, ActivityDataUpdate(extra_fields=ef))


async def _set_links_on_sources(
    db: AsyncSession,
    source_rows: Sequence[ActivityData],
    mitigation_id: UUID,
) -> None:
    mid_str = str(mitigation_id)
    for row in source_rows:
        ef = dict(row.extra_fields or {})
        ef[AUTO_ELECTRICITY_LINK_KEY] = mid_str
        await update_activity_data(db, row.id, ActivityDataUpdate(extra_fields=ef))


def _build_leg_payloads(
    leg_rows: List[Dict[str, Any]],
    *,
    project_id: UUID,
    mit_si_id: UUID,
    mit_opt_id: Optional[UUID],
    ui_table_key: str,
    mitigation_id: UUID,
    dataset_revision_id: Optional[UUID],
    submission_period_id: Optional[UUID],
    created_by: Optional[UUID],
) -> List[ActivityDataCreate]:
    payloads: List[ActivityDataCreate] = []
    for row in leg_rows:
        extra = dict(row)
        qty = Decimal(str(row["quantity_mwh"]))
        payloads.append(
            ActivityDataCreate(
                project_id=project_id,
                project_stage_instance_id=mit_si_id,
                project_option_id=mit_opt_id,
                quantity=qty,
                unit_id=None,
                ui_table_key=ui_table_key,
                extra_fields=extra,
                project_mitigation_id=mitigation_id,
                dataset_revision_id=dataset_revision_id,
                submission_period_id=submission_period_id,
                created_by=created_by,
            )
        )
    return payloads


async def sync_auto_electricity_for_table(
    db: AsyncSession,
    stage_instance: ProjectStageInstance,
    ui_table_key: str,
    project_option_id: Optional[UUID],
    submission_period_id: Optional[UUID] = None,
    project: Optional[Project] = None,
    known_mitigation_id: Optional[UUID] = None,
) -> None:
    """Create/update/delete auto electricity substitution for one table bucket."""
    if ui_table_key not in AUTO_ELECTRICITY_TABLE_KEYS:
        return

    lc_meta = electricity_lifecycle_meta(ui_table_key)
    if lc_meta is None:
        return

    stage_label = submission_stage_label(stage_instance.stage)
    if stage_label is None:
        return

    proj = project
    if proj is None and stage_instance.project_id:
        proj = await get_project(db, stage_instance.project_id)
    if proj is None or proj.project_class != ProjectClass.LARGE:
        return

    source_rows = await _load_source_rows(
        db,
        stage_instance.id,
        ui_table_key,
        project_option_id,
        submission_period_id,
    )

    linked_mid = known_mitigation_id
    if linked_mid is None:
        for row in source_rows:
            linked_mid = _mitigation_id_from_extra(row.extra_fields)
            if linked_mid:
                break

    if not _has_renewable_trigger(source_rows):
        if linked_mid:
            await delete_project_mitigation(db, linked_mid)
        await _clear_links_on_sources(db, source_rows)
        return

    if not source_rows:
        return

    jurisdiction_id = await _resolve_jurisdiction_id(db, proj)
    if jurisdiction_id is None:
        logger.warning(
            "Auto electricity skipped: no jurisdiction for project=%s",
            proj.id,
        )
        return

    dataset_revision_id = await _resolve_dataset_revision_id(db, proj.id, source_rows)
    era_bau_pcts = await load_era_bau_pcts_for_jurisdiction(
        db, dataset_revision_id, jurisdiction_id, ui_table_key
    )

    adopted_data = consolidate_adopted_rows(source_rows)
    replaced_data = build_replaced_rows(source_rows, era_bau_pcts)

    mit_si_id, mit_opt_id = await mitigation_listing_stage_and_option(
        db, proj.id, stage_instance, project_option_id
    )
    lifecycle_phase, lifecycle_phase_label = lc_meta
    replaced_key, adopted_key = mitigation_substitution_ui_keys(ui_table_key)

    mitigation_payload = {
        "project_id": proj.id,
        "project_stage_instance_id": mit_si_id,
        "project_option_id": mit_opt_id,
        "submission_stage": stage_label,
        "name": _MITIGATION_NAMES.get(ui_table_key, "Auto Triggered Electricity"),
        "mitigation_type": "substitution",
        "lifecycle_phase": lifecycle_phase,
        "lifecycle_phase_label": lifecycle_phase_label,
        "notes": None,
        "group_label": None,
    }

    created_by = source_rows[0].created_by if source_rows else None

    if linked_mid:
        existing_pm = await get_project_mitigation(db, linked_mid)
        if existing_pm:
            await update_project_mitigation(db, linked_mid, mitigation_payload)
            mitigation_id = linked_mid
        else:
            pm = await create_project_mitigation(db, mitigation_payload)
            mitigation_id = pm.id
    else:
        pm = await create_project_mitigation(db, mitigation_payload)
        mitigation_id = pm.id

    common_kwargs = dict(
        project_id=proj.id,
        mit_si_id=mit_si_id,
        mit_opt_id=mit_opt_id,
        mitigation_id=mitigation_id,
        dataset_revision_id=dataset_revision_id,
        submission_period_id=submission_period_id,
        created_by=created_by,
    )

    adopted_payloads = _build_leg_payloads(
        adopted_data, ui_table_key=adopted_key, **common_kwargs
    )
    replaced_payloads = _build_leg_payloads(
        replaced_data, ui_table_key=replaced_key, **common_kwargs
    )

    adopted_saved = await bulk_upsert_activity_data(
        db, mit_si_id, adopted_key, adopted_payloads, project_mitigation_id=mitigation_id
    )
    replaced_saved = await bulk_upsert_activity_data(
        db, mit_si_id, replaced_key, replaced_payloads, project_mitigation_id=mitigation_id
    )

    from services.emissions_calculator import calculate_and_store

    for leg_row in adopted_saved + replaced_saved:
        await calculate_and_store(db, leg_row)

    await _set_links_on_sources(db, source_rows, mitigation_id)


async def preclean_linked_auto_electricity_mitigations(
    db: AsyncSession,
    stage_instance_id: UUID,
    ui_table_key: str,
    payload_rows: Sequence[ActivityDataCreate],
) -> None:
    """Before bulk replace, delete linked mitigations for affected buckets."""
    if ui_table_key not in AUTO_ELECTRICITY_TABLE_KEYS:
        return

    buckets = {_bucket_key(r.project_option_id, r.submission_period_id) for r in payload_rows}
    seen_mids: Set[UUID] = set()

    for opt_id, period_id in buckets:
        q = select(ActivityData).where(
            ActivityData.project_stage_instance_id == stage_instance_id,
            ActivityData.ui_table_key == ui_table_key,
            ActivityData.project_mitigation_id.is_(None),
        )
        if opt_id is not None:
            q = q.where(ActivityData.project_option_id == opt_id)
        else:
            q = q.where(ActivityData.project_option_id.is_(None))
        if period_id is not None:
            q = q.where(ActivityData.submission_period_id == period_id)
        else:
            q = q.where(ActivityData.submission_period_id.is_(None))

        existing = list((await db.execute(q)).scalars().all())
        for ex in existing:
            mid = _mitigation_id_from_extra(ex.extra_fields)
            if mid and mid not in seen_mids:
                seen_mids.add(mid)
                await delete_project_mitigation(db, mid)
        await _clear_links_on_sources(db, existing)


async def sync_auto_electricity_after_row_change(
    db: AsyncSession,
    row: ActivityData,
    stage_instance: ProjectStageInstance,
    project: Optional[Project] = None,
) -> None:
    """Re-sync the bucket for a single source electricity row."""
    if row.project_mitigation_id is not None:
        return
    if row.ui_table_key not in AUTO_ELECTRICITY_TABLE_KEYS:
        return
    await sync_auto_electricity_for_table(
        db,
        stage_instance,
        row.ui_table_key,
        row.project_option_id,
        row.submission_period_id,
        project=project,
    )


async def resync_auto_electricity_bucket_after_delete(
    db: AsyncSession,
    stage_instance: ProjectStageInstance,
    ui_table_key: str,
    project_option_id: Optional[UUID],
    submission_period_id: Optional[UUID],
    project: Optional[Project] = None,
    known_mitigation_id: Optional[UUID] = None,
) -> None:
    """Re-sync bucket after a source row was deleted."""
    if ui_table_key not in AUTO_ELECTRICITY_TABLE_KEYS:
        return
    await sync_auto_electricity_for_table(
        db,
        stage_instance,
        ui_table_key,
        project_option_id,
        submission_period_id,
        project=project,
        known_mitigation_id=known_mitigation_id,
    )
