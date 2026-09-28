"""
Auto-triggered Substitution mitigations for LARGE-project Grade 3 activity rows.

Orchestrates ProjectMitigation + mitigation-scoped activity_data twin legs when a row
matches Direct Substitution factors for the project's jurisdiction.
"""

from __future__ import annotations

import copy
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.activity_data import bulk_upsert_activity_data, update_activity_data
from crud.organization import get_organization
from crud.project import get_project
from crud.project_mitigations import (
    create_project_mitigation,
    delete_project_mitigation,
    get_project_mitigation,
    update_project_mitigation,
)
from crud.units import get_unit_by_code
from models.activity_data import ActivityData
from models.direct_substitution_factors import DirectSubstitutionFactor
from models.jurisdictions import Jurisdiction
from models.project import Project, ProjectClass
from models.project_options import ProjectOption
from models.project_stage_instances import ProjectStage, ProjectStageInstance
from schemas.activity_data import ActivityDataCreate, ActivityDataUpdate
from services.project_context_helper import ProjectContextHelper

logger = logging.getLogger(__name__)

AUTO_SUBSTITUTION_LINK_KEY = "auto_substitution_mitigation_id"

# Copied from source extra_fields; must not mask recalculated leg totals in UI/dashboards.
_COPIED_EMISSION_KEYS: Tuple[str, ...] = (
    "total_emissions_tco2e",
    "emissions_tco2e",
    "product_stage_a1_a3_tco2e",
    "transport_stage_a4_tco2e",
    "construction_stage_a5_tco2e",
    "scope1_emissions_tco2e",
    "scope3_emissions_tco2e",
)

_CANONICAL_UNIT_KEYS: Tuple[str, ...] = (
    "canonical_unit_id",
    "unit_conversion_factor",
    "canonical_unit_code",
)

# Construction Detailed Level (Grade 3) only — Design uses bcDetailedLevel, Construction uses constructionG3.
# O&M Grade 3 tables are explicitly excluded from auto substitution.
AUTO_SUBSTITUTION_TABLE_KEYS: frozenset[str] = frozenset(
    {
        "bcDetailedLevel",
        "constructionG3",
    }
)

# Retired keys (previously auto-synced); used for one-off data cleanup migrations.
RETIRED_AUTO_SUBSTITUTION_OM_TABLE_KEYS: frozenset[str] = frozenset(
    {"useB1G3", "replDetailed", "opEnergyDetailed"}
)


def pick_emissions_source_label(raw: Any) -> str:
    """Mirror frontend pickLabel(emissions_source_name) semantics."""
    if raw is None:
        return ""
    if isinstance(raw, (str, int, float)):
        return str(raw)
    if isinstance(raw, dict):
        return str(raw.get("label") or raw.get("name") or raw.get("value") or "")
    return ""


def pick_unit_label(extra: Optional[Dict[str, Any]]) -> str:
    if not extra:
        return ""
    return pick_emissions_source_label(extra.get("unit_code"))


def _norm_match_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


async def mitigation_listing_stage_and_option(
    db: AsyncSession,
    project_id: UUID,
    source_si: ProjectStageInstance,
    source_option_id: Optional[UUID],
) -> Tuple[UUID, Optional[UUID]]:
    """
    Mitigations landing + activity fetches scope mitigations under the Design or Construction
    stage instance only. Persist auto mitigations there and map project_option_id to an option
    on that instance (same report_number + option_number) so the listing filter and fetches align.
    """
    if source_si.stage == ProjectStage.CONSTRUCTION:
        tgt_si_id = source_si.id
    else:
        dq = await db.execute(
            select(ProjectStageInstance).where(
                ProjectStageInstance.project_id == project_id,
                ProjectStageInstance.stage == ProjectStage.DESIGN,
            )
        )
        design_si = dq.scalars().first()
        tgt_si_id = design_si.id if design_si else source_si.id

    tgt_opt_id: Optional[UUID] = source_option_id
    if tgt_opt_id is None:
        return tgt_si_id, None

    opt_res = await db.execute(select(ProjectOption).where(ProjectOption.id == tgt_opt_id))
    src_opt = opt_res.scalars().first()
    if not src_opt:
        return tgt_si_id, None

    if src_opt.stage_instance_id == tgt_si_id:
        return tgt_si_id, tgt_opt_id

    mapped_res = await db.execute(
        select(ProjectOption)
        .where(
            ProjectOption.project_id == project_id,
            ProjectOption.stage_instance_id == tgt_si_id,
            ProjectOption.report_number == src_opt.report_number,
            ProjectOption.option_number == src_opt.option_number,
        )
        .limit(1)
    )
    mapped = mapped_res.scalars().first()
    if mapped:
        return tgt_si_id, mapped.id

    logger.warning(
        "Auto substitution: no project_option remap for mitigation listing SI %s "
        "(source option %s report=%s opt#=%s); storing mitigation without option id",
        tgt_si_id,
        tgt_opt_id,
        src_opt.report_number,
        src_opt.option_number,
    )
    return tgt_si_id, None


def submission_stage_label(stage: ProjectStage) -> Optional[str]:
    if stage == ProjectStage.DESIGN:
        return "Design"
    if stage == ProjectStage.CONSTRUCTION:
        return "Construction"
    return None


def substitution_lifecycle_meta(
    ui_table_key: str, stage: ProjectStage
) -> Optional[Tuple[str, str]]:
    """
    Returns (lifecycle_phase, lifecycle_phase_label) when the row is eligible.

    Only construction-phase Detailed Level tables participate: **bcDetailedLevel** (Design
    submission) and **constructionG3** (Construction submission). O&M Grade 3 keys are
    not eligible for auto substitution.
    """
    if ui_table_key == "bcDetailedLevel":
        if stage != ProjectStage.DESIGN:
            return None
        return ("construction", "Construction")
    if ui_table_key == "constructionG3":
        if stage != ProjectStage.CONSTRUCTION:
            return None
        return ("construction", "Construction")
    return None


def mitigation_substitution_ui_keys(base_key: str) -> Tuple[str, str]:
    replaced_key = f"{base_key}-mitigation-subst-replaced"
    adopted_key = f"{base_key}-mitigation-subst-adopted"
    return replaced_key, adopted_key


def _mitigation_id_from_extra(extra: Optional[Dict[str, Any]]) -> Optional[UUID]:
    raw = (extra or {}).get(AUTO_SUBSTITUTION_LINK_KEY)
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None


async def _load_substitution_factors(
    db: AsyncSession,
    jurisdiction_id: UUID,
    dataset_revision_id: Optional[UUID] = None,
) -> List[DirectSubstitutionFactor]:
    q = (
        select(DirectSubstitutionFactor)
        .where(DirectSubstitutionFactor.jurisdiction_id == jurisdiction_id)
        .order_by(
            DirectSubstitutionFactor.display_order,
            DirectSubstitutionFactor.user_emissions_source,
            DirectSubstitutionFactor.user_unit,
        )
    )
    if dataset_revision_id is not None:
        q = q.where(DirectSubstitutionFactor.dataset_revision_id == dataset_revision_id)
    res = await db.execute(q)
    return list(res.scalars().unique().all())


def _pick_direct_substitution_factor(
    factors: Sequence[DirectSubstitutionFactor],
    user_emissions_source_label: str,
    row_unit_label: str,
) -> Optional[DirectSubstitutionFactor]:
    label_norm = _norm_match_text(user_emissions_source_label)
    if not label_norm:
        return None

    candidates = [
        f
        for f in factors
        if _norm_match_text(f.user_emissions_source or "") == label_norm
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    unit_norm = _norm_match_text(row_unit_label)
    if unit_norm:
        unit_matches = [
            f
            for f in candidates
            if _norm_match_text(f.user_unit or "") == unit_norm
        ]
        if len(unit_matches) == 1:
            return unit_matches[0]
        if len(unit_matches) > 1:
            logger.warning(
                "Direct substitution: multiple factors match source %r and unit %r; using first",
                user_emissions_source_label,
                row_unit_label,
            )
            return unit_matches[0]

    logger.warning(
        "Direct substitution: multiple factors match source %r without resolvable unit tie-break; using first",
        user_emissions_source_label,
    )
    return candidates[0]


def _truncate512(name: str) -> str:
    return name if len(name) <= 512 else name[:512]


def strip_copied_emission_fields(extra_fields: Dict[str, Any]) -> None:
    """Remove emission totals/breakdown copied from the source row before leg upsert."""
    for key in _COPIED_EMISSION_KEYS:
        extra_fields.pop(key, None)


def clear_stale_unit_conversion_for_bau_unit(
    extra_fields: Dict[str, Any],
    source_unit_label: str,
    bau_unit_code: str,
) -> None:
    """
    Drop canonical conversion metadata from the source row when the BAU unit differs,
    so grade34 recalc does not apply the user unit's factor to BAU quantity.
    """
    if _norm_match_text(source_unit_label) == _norm_match_text(bau_unit_code):
        return
    for key in _CANONICAL_UNIT_KEYS:
        extra_fields.pop(key, None)


async def _persist_leg_emissions_to_extra_fields(
    db: AsyncSession,
    leg_row: ActivityData,
    total: Decimal,
) -> None:
    ef = dict(leg_row.extra_fields or {})
    total_float = float(total)
    ef["total_emissions_tco2e"] = total_float
    ef["emissions_tco2e"] = total_float
    await update_activity_data(db, leg_row.id, ActivityDataUpdate(extra_fields=ef))
    leg_row.extra_fields = ef


async def _resolve_jurisdiction_id(db: AsyncSession, project: Project) -> Optional[UUID]:
    """
    Direct substitution rows are keyed by jurisdictions.id.

    Prefer organization.jurisdiction_id. If unset, mirror emission calculators via
    ProjectContextHelper.fetch_jurisdiction (defaults to Australia) and resolve the
    jurisdictions row by name — otherwise matching never runs while calcs still work.
    """
    org = await get_organization(db, project.proponent_org_id)
    if org is not None and org.jurisdiction_id is not None:
        return org.jurisdiction_id

    jur_name = await ProjectContextHelper.fetch_jurisdiction(db, project.id)
    res = await db.execute(select(Jurisdiction.id).where(Jurisdiction.name == jur_name))
    return res.scalar_one_or_none()


async def delete_linked_auto_substitution_mitigation(db: AsyncSession, row: ActivityData) -> None:
    """Remove mitigation referenced by source row extra_fields (no-op if absent)."""
    mid = _mitigation_id_from_extra(row.extra_fields)
    if mid is None:
        return
    await delete_project_mitigation(db, mid)


async def preclean_linked_auto_substitution_mitigations(
    db: AsyncSession,
    stage_instance_id: UUID,
    ui_table_key: str,
    payload_rows: Sequence[ActivityDataCreate],
) -> None:
    """
    Before bulk replace of eligible source tables, delete mitigations linked from rows
    that are about to be wiped (same bucket as bulk_upsert_activity_data).
    """
    if ui_table_key not in AUTO_SUBSTITUTION_TABLE_KEYS:
        return

    option_ids = {r.project_option_id for r in payload_rows}
    seen_mids: set[UUID] = set()

    for opt_id in option_ids:
        q = select(ActivityData).where(
            ActivityData.project_stage_instance_id == stage_instance_id,
            ActivityData.ui_table_key == ui_table_key,
            ActivityData.project_option_id == opt_id,
            ActivityData.project_mitigation_id.is_(None),
        )
        existing = (await db.execute(q)).scalars().all()
        for ex in existing:
            mid = _mitigation_id_from_extra(ex.extra_fields)
            if mid and mid not in seen_mids:
                seen_mids.add(mid)
                await delete_project_mitigation(db, mid)


async def _clear_link_on_source(db: AsyncSession, row_id: UUID, extra: Optional[Dict[str, Any]]) -> None:
    ef = dict(extra or {})
    ef.pop(AUTO_SUBSTITUTION_LINK_KEY, None)
    await update_activity_data(db, row_id, ActivityDataUpdate(extra_fields=ef))


async def sync_auto_substitution_for_source_row(
    db: AsyncSession,
    row: ActivityData,
    stage_instance: ProjectStageInstance,
    project: Optional[Project] = None,
) -> None:
    """
    Create/update/delete auto Substitution mitigation + twin mitigation rows for one source activity row.
    Idempotent within the current transaction; expects caller to refresh ORM row after commit as needed.
    """
    if row.project_mitigation_id is not None:
        return

    lc_meta = substitution_lifecycle_meta(row.ui_table_key, stage_instance.stage)
    if lc_meta is None:
        return

    proj = project or await get_project(db, row.project_id)
    if proj is None or proj.project_class != ProjectClass.LARGE:
        logger.debug(
            "Auto substitution skipped: project=%s not LARGE (%s)",
            row.project_id,
            getattr(proj, "project_class", None),
        )
        return

    jurisdiction_id = await _resolve_jurisdiction_id(db, proj)
    if jurisdiction_id is None:
        logger.warning(
            "Auto substitution skipped: could not resolve jurisdiction UUID for project=%s",
            row.project_id,
        )
        return

    stage_label = submission_stage_label(stage_instance.stage)
    if stage_label is None:
        return

    mit_si_id, mit_opt_id = await mitigation_listing_stage_and_option(
        db, row.project_id, stage_instance, row.project_option_id
    )

    lifecycle_phase, lifecycle_phase_label = lc_meta
    base_key = row.ui_table_key
    replaced_key, adopted_key = mitigation_substitution_ui_keys(base_key)

    extra = row.extra_fields or {}
    user_source_label = pick_emissions_source_label(extra.get("emissions_source_name"))
    row_unit_label = pick_unit_label(extra)

    factors = await _load_substitution_factors(
        db, jurisdiction_id, row.dataset_revision_id
    )
    factor = _pick_direct_substitution_factor(factors, user_source_label, row_unit_label)

    linked_mid = _mitigation_id_from_extra(extra)

    if factor is None:
        logger.debug(
            "Auto substitution: no DS row for jurisdiction=%s table=%s source=%r unit=%r",
            jurisdiction_id,
            row.ui_table_key,
            user_source_label,
            row_unit_label,
        )
        if linked_mid:
            await delete_project_mitigation(db, linked_mid)
            await _clear_link_on_source(db, row.id, row.extra_fields)
        return

    mit_name = _truncate512(f"Auto Triggered {user_source_label}")

    mitigation_payload = {
        "project_id": row.project_id,
        "project_stage_instance_id": mit_si_id,
        "project_option_id": mit_opt_id,
        "submission_stage": stage_label,
        "name": mit_name,
        "mitigation_type": "substitution",
        "lifecycle_phase": lifecycle_phase,
        "lifecycle_phase_label": lifecycle_phase_label,
        "notes": None,
        "group_label": None,
    }

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

    bau_unit = await get_unit_by_code(db, factor.bau_equivalent_unit)

    adopted_ef = copy.deepcopy(extra)
    adopted_ef.pop(AUTO_SUBSTITUTION_LINK_KEY, None)
    strip_copied_emission_fields(adopted_ef)

    replaced_ef = copy.deepcopy(extra)
    replaced_ef.pop(AUTO_SUBSTITUTION_LINK_KEY, None)
    replaced_ef["emissions_source_name"] = factor.bau_equivalent_emission_source
    replaced_ef.pop("emissions_source", None)
    replaced_ef["unit_code"] = factor.bau_equivalent_unit
    if bau_unit:
        replaced_ef["unit_label"] = bau_unit.label or bau_unit.code
    strip_copied_emission_fields(replaced_ef)
    clear_stale_unit_conversion_for_bau_unit(
        replaced_ef,
        row_unit_label,
        factor.bau_equivalent_unit,
    )

    qty_src = Decimal(str(row.quantity))
    ratio = Decimal(str(factor.bau_quantity_per_user_unit))
    replaced_qty = qty_src * ratio

    common_kwargs = dict(
        project_id=row.project_id,
        project_stage_instance_id=mit_si_id,
        project_option_id=mit_opt_id,
        component_id=row.component_id,
        dataset_revision_id=row.dataset_revision_id,
        metric_natural_key=copy.deepcopy(row.metric_natural_key)
        if row.metric_natural_key is not None
        else None,
        lifecycle_module_code=row.lifecycle_module_code,
        submission_period_id=row.submission_period_id,
        created_by=row.created_by,
    )

    adopted_payload = ActivityDataCreate(
        **common_kwargs,
        quantity=row.quantity,
        unit_id=row.unit_id,
        ui_table_key=adopted_key,
        extra_fields=adopted_ef,
        project_mitigation_id=mitigation_id,
    )

    replaced_payload = ActivityDataCreate(
        **common_kwargs,
        quantity=replaced_qty,
        unit_id=bau_unit.id if bau_unit else row.unit_id,
        ui_table_key=replaced_key,
        extra_fields=replaced_ef,
        project_mitigation_id=mitigation_id,
    )

    adopted_rows = await bulk_upsert_activity_data(
        db,
        mit_si_id,
        adopted_key,
        [adopted_payload],
        project_mitigation_id=mitigation_id,
    )
    replaced_rows = await bulk_upsert_activity_data(
        db,
        mit_si_id,
        replaced_key,
        [replaced_payload],
        project_mitigation_id=mitigation_id,
    )

    # Deferred import avoids circular imports with emissions_calculator.
    from services.emissions_calculator import calculate_and_store

    for leg_rows in (adopted_rows, replaced_rows):
        for leg_row in leg_rows:
            total = await calculate_and_store(db, leg_row)
            if total is not None:
                await _persist_leg_emissions_to_extra_fields(db, leg_row, total)

    new_extra = dict(extra)
    new_extra[AUTO_SUBSTITUTION_LINK_KEY] = str(mitigation_id)
    await update_activity_data(db, row.id, ActivityDataUpdate(extra_fields=new_extra))
