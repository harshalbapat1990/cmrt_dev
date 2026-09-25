from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import cast, func, update
from sqlalchemy import Numeric as SANumeric

from models.activity_data import ActivityData
from models.project_options import ProjectOption
from models.project_stage_instances import ProjectStageInstance
from schemas.project_options import ProjectOptionCreate


_STAGE_ENUM_TO_LABEL: dict = {
    "BUSINESS_CASE": "Business case",
    "DESIGN": "Design",
    "CONSTRUCTION": "Construction",
}


async def create_project_option(db: AsyncSession, payload: ProjectOptionCreate) -> ProjectOption:
    obj = ProjectOption(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_project_option(db: AsyncSession, option_id: UUID) -> Optional[ProjectOption]:
    result = await db.execute(select(ProjectOption).where(ProjectOption.id == option_id))
    return result.scalars().first()


async def list_project_options(
    db: AsyncSession,
    project_id: UUID,
    stage_instance_id: UUID,
    report_number: Optional[int] = None,
) -> List[ProjectOption]:
    q = (
        select(ProjectOption)
        .where(
            ProjectOption.project_id == project_id,
            ProjectOption.stage_instance_id == stage_instance_id,
        )
        .order_by(ProjectOption.report_number, ProjectOption.option_number)
    )
    if report_number is not None:
        q = q.where(ProjectOption.report_number == report_number)
    result = await db.execute(q)
    return result.scalars().all()


async def get_or_create_options_for_stage(
    db: AsyncSession,
    stage_instance: ProjectStageInstance,
) -> List[ProjectOption]:
    n = stage_instance.num_reports_required or 1
    stage_label = _STAGE_ENUM_TO_LABEL.get(stage_instance.stage.value if hasattr(stage_instance.stage, 'value') else str(stage_instance.stage), "Option")
    existing = await list_project_options(db, stage_instance.project_id, stage_instance.id)

    existing_pairs = {(o.report_number, o.option_number) for o in existing}

    for report_num in range(1, n + 1):
        if (report_num, 1) not in existing_pairs:
            new_opt = ProjectOption(
                project_id=stage_instance.project_id,
                stage_instance_id=stage_instance.id,
                report_number=report_num,
                option_number=1,
                label=f"{stage_label} - option 1",
                is_default=True,
            )
            db.add(new_opt)

    await db.flush()
    return await list_project_options(db, stage_instance.project_id, stage_instance.id)


async def create_sub_option(
    db: AsyncSession,
    project_id: UUID,
    stage_instance_id: UUID,
    report_number: int,
    label: str,
) -> ProjectOption:
    q = (
        select(ProjectOption)
        .where(
            ProjectOption.stage_instance_id == stage_instance_id,
            ProjectOption.report_number == report_number,
        )
        .order_by(ProjectOption.option_number.desc())
    )
    last = (await db.execute(q)).scalars().first()
    next_num = (last.option_number + 1) if last else 1

    obj = ProjectOption(
        project_id=project_id,
        stage_instance_id=stage_instance_id,
        report_number=report_number,
        option_number=next_num,
        label=label,
        is_default=False,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def rename_project_option(
    db: AsyncSession, option_id: UUID, label: str
) -> Optional[ProjectOption]:
    obj = await get_project_option(db, option_id)
    if not obj:
        return None
    obj.label = label
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def set_default_project_option(
    db: AsyncSession, option_id: UUID
) -> Optional[ProjectOption]:
    obj = await get_project_option(db, option_id)
    if not obj:
        return None

    q = select(ProjectOption).where(
        ProjectOption.stage_instance_id == obj.stage_instance_id,
        ProjectOption.report_number == obj.report_number,
        ProjectOption.is_default == True,
    )
    for existing_default in (await db.execute(q)).scalars().all():
        existing_default.is_default = False
        db.add(existing_default)

    obj.is_default = True
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_project_option(db: AsyncSession, option_id: UUID) -> bool:
    obj = await get_project_option(db, option_id)
    if not obj:
        return False
    if obj.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the base case option. Set another option as base case first.",
        )
    q = select(ActivityData).where(ActivityData.project_option_id == option_id)
    for ad_row in (await db.execute(q)).scalars().all():
        await db.delete(ad_row)
    await db.flush()
    await db.delete(obj)
    await db.flush()
    return True


# ---------------------------------------------------------------------------
# Emissions total helper
# ---------------------------------------------------------------------------

# Keys whose emissions are read from extra_fields["total_emissions_tco2e"].
# Includes both small-project and large-project table keys.
# Explicitly excluded from this set (never summed here):
#   - any key with "-mitigation" suffix (mitigations use their own keyed rows)
#   - constructionG2, constructionG3 (construction-stage only)
#   - largeRoadUsers (no total emission value stored in activity_data.extra_fields)
#   - recurringG3 (planned future key, not yet implemented)
# Rail-users handled separately via _RAIL_TABLE_KEYS (emissions_total_ref_period_tco2e).
# Road-users handled separately via _ROAD_TABLE_KEYS (final_user_emissions_tco2e).
# largeRoadParams handled separately — one-row-only read (final_user_emissions_tco2e).
_STANDARD_TABLE_KEYS = {
    # ---- small project ----
    "asset", "component", "componentRepl", "refurbishment",
    # ---- large project (additional) ----
    "bcDetailedLevel",
    "electricity",
    "opEnergyElectricity",
    "useB1G2",
    "useB1G3",
    "replDetailed",
    "opEnergyDetailed",
    "concreteRegSimplified",
    "concreteRegDetailed",
}

# Rail-users keys store emissions_total_ref_period_tco2e in extra_fields.
_RAIL_TABLE_KEYS = {"railUsers", "largeRailUsers"}

# Road-users keys store final_user_emissions_tco2e in extra_fields.
# largeRoadUsers is excluded — no emission value stored in its rows.
_ROAD_TABLE_KEYS = {"roadUsers"}

# Keys where the frontend stores separate location-based and market-based totals
# instead of a single total_emissions_tco2e value.
_GRADE2_TABLE_KEYS = {"opEnergy"}


async def get_total_emissions_for_option(
    db: AsyncSession,
    option_id: UUID,
) -> Decimal:
    """
    Sum all tCO₂e emissions for a given project option across all tables.
    All values are read exclusively from ``activity_data.extra_fields`` JSONB.

    Standard keys (small + large project):
        asset, component, componentRepl, refurbishment,
        bcDetailedLevel, electricity, opEnergyElectricity,
        useB1G2, useB1G3, replDetailed, opEnergyDetailed,
        concreteRegSimplified, concreteRegDetailed
        → extra_fields["total_emissions_tco2e"]

    shortcutIsMaterials:
        → SUM extra_fields["actual_case"]

    shortcutSat4p:
        → SUM extra_fields["actual_scope3"] + extra_fields["actual_scope4"]

    Rail-users keys:
        railUsers, largeRailUsers
        → SUM extra_fields["emissions_total_ref_period_tco2e"]

    Road-users keys:
        roadUsers
        → SUM extra_fields["final_user_emissions_tco2e"] (one row per vehicle type)

    largeRoadParams:
        → extra_fields["final_user_emissions_tco2e"] from ONE row only
          (multiple rows exist — one per modelled year — all holding the same total;
           LIMIT 1 avoids multiplying the value by the number of modelled years)

    opEnergy (location/market-based):
        → extra_fields["location_based_total_tco2e"] +
          extra_fields["market_based_total_tco2e"]

    Excluded: -mitigation keys, constructionG2/G3, largeRoadUsers,
              concreteRegSimplified, recurringG3
    """
    # NULLIF(..., '-') converts the frontend placeholder "-" to NULL before
    # casting, allowing COALESCE to fall back to 0 safely.
    ef_total_col = func.coalesce(
        cast(func.nullif(ActivityData.extra_fields["total_emissions_tco2e"].astext, "-"), SANumeric),
        0,
    )

    # 1. asset / component / componentRepl / refurbishment
    standard_total = Decimal(0)
    for key in _STANDARD_TABLE_KEYS:
        key_q = (
            select(func.coalesce(func.sum(ef_total_col), 0))
            .where(
                ActivityData.project_option_id == option_id,
                ActivityData.ui_table_key == key,
            )
        )
        key_total = (await db.execute(key_q)).scalar() or Decimal(0)
        standard_total += Decimal(str(key_total))

    # 2. opEnergy — location-based + market-based totals
    lb_col = func.coalesce(
        cast(func.nullif(ActivityData.extra_fields["location_based_total_tco2e"].astext, "-"), SANumeric),
        0,
    )
    mb_col = func.coalesce(
        cast(func.nullif(ActivityData.extra_fields["market_based_total_tco2e"].astext, "-"), SANumeric),
        0,
    )
    op_q = (
        select(func.coalesce(func.sum(lb_col + mb_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key.in_(_GRADE2_TABLE_KEYS),
        )
    )
    op_total = (await db.execute(op_q)).scalar() or Decimal(0)

    # 3. railUsers / largeRailUsers — emissions_total_ref_period_tco2e
    rail_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["emissions_total_ref_period_tco2e"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    rail_q = (
        select(func.coalesce(func.sum(rail_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key.in_(_RAIL_TABLE_KEYS),
        )
    )
    rail_total = (await db.execute(rail_q)).scalar() or Decimal(0)

    # 4. roadUsers — SUM final_user_emissions_tco2e (one row per vehicle type)
    road_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["final_user_emissions_tco2e"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    road_q = (
        select(func.coalesce(func.sum(road_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key.in_(_ROAD_TABLE_KEYS),
        )
    )
    road_total = (await db.execute(road_q)).scalar() or Decimal(0)

    # 5. largeRoadParams — final_user_emissions_tco2e from ONE row only.
    #    Multiple rows exist (one per modelled year) but each carries the same
    #    grand-total value; LIMIT 1 prevents multiplying by the number of years.
    params_q = (
        select(
            func.coalesce(
                cast(
                    func.nullif(ActivityData.extra_fields["final_user_emissions_tco2e"].astext, "-"),
                    SANumeric,
                ),
                0,
            )
        )
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key == "largeRoadParams",
        )
        .limit(1)
    )
    params_total = (await db.execute(params_q)).scalar() or Decimal(0)

    uplift_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["upscaling_adjustment_tco2e"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    uplift_q = (
        select(func.coalesce(func.sum(uplift_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key == "completeness",
        )
    )
    uplift_total = (await db.execute(uplift_q)).scalar() or Decimal(0)

    # 6. shortcutIsMaterials — SUM actual_case
    shortcut_is_materials_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["actual_case"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    shortcut_is_materials_q = (
        select(func.coalesce(func.sum(shortcut_is_materials_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key == "shortcutIsMaterials",
        )
    )
    shortcut_is_materials_total = (await db.execute(shortcut_is_materials_q)).scalar() or Decimal(0)

    # 7. shortcutSat4p — SUM actual_scope3 + actual_scope4
    shortcut_sat4p_scope3_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["actual_scope3"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    shortcut_sat4p_scope4_col = func.coalesce(
        cast(
            func.nullif(ActivityData.extra_fields["actual_scope4"].astext, "-"),
            SANumeric,
        ),
        0,
    )
    shortcut_sat4p_q = (
        select(func.coalesce(func.sum(shortcut_sat4p_scope3_col + shortcut_sat4p_scope4_col), 0))
        .where(
            ActivityData.project_option_id == option_id,
            ActivityData.ui_table_key == "shortcutSat4p",
        )
    )
    shortcut_sat4p_total = (await db.execute(shortcut_sat4p_q)).scalar() or Decimal(0)

    grand_total = round(
        standard_total
        + Decimal(str(op_total))
        + Decimal(str(rail_total))
        + Decimal(str(road_total))
        + Decimal(str(params_total))
        + Decimal(str(uplift_total))
        + Decimal(str(shortcut_is_materials_total))
        + Decimal(str(shortcut_sat4p_total)),
        6,
    )
    return grand_total


async def set_report_options_status(
    db: AsyncSession,
    stage_instance_id: UUID,
    report_number: int,
    new_status: str,
    justification: Optional[str] = None,
) -> List[ProjectOption]:
    q = select(ProjectOption).where(
        ProjectOption.stage_instance_id == stage_instance_id,
        ProjectOption.report_number == report_number,
    )
    options = (await db.execute(q)).scalars().all()
    for opt in options:
        opt.approval_status = new_status
        if justification is not None:
            opt.current_justification = justification
        elif new_status == "draft":
            opt.current_justification = None
        db.add(opt)
    await db.flush()
    for opt in options:
        await db.refresh(opt)
    return list(options)