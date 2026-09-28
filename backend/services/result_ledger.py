"""Populate canonical emissions result facts from calculated row outputs.

Calculators may continue placing output fields in extra_fields for older clients;
this adapter persists those values into emissions_results so reports consume one
normalized ledger. It only creates supported facts and never guesses a factor.
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from crud.emissions_results import upsert_result
from models.activity_data import ActivityData
from models.emissions_results import EmissionsResult
from models.project import Project
from sqlalchemy import text


def _number(value: Any) -> Optional[Decimal]:
    if value in (None, "", "-"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


async def persist_legacy_outputs(db: AsyncSession, row: ActivityData) -> int:
    """Mirror valid calculated outputs for a row into structured result facts."""
    extra = row.extra_fields or {}
    key = row.ui_table_key or ""
    base = key.split("-mitigation", 1)[0]
    module_values: list[tuple[str, str, Any, str]] = []

    if key == "completeness":
        module_names = {
            "a1_a3": "A1-A3", "a4": "A4", "a5": "A5", "b1": "B1",
            "b2_b5": "B2-5", "b6": "B6", "b7": "B7",
        }
        module = module_names.get(str(extra.get("module") or "").lower())
        adjustment = _number(extra.get("upscaling_adjustment_tco2e"))
        if module and adjustment is not None:
            module_values.append((f"upscaling_{module}", module, adjustment, "common"))

    # Stored carbon is a calculated result, not a dashboard-time calculation.
    # Keep the lookup join here so create/edit and historical backfill use the
    # same emissions_results value.
    if key in {"component", "bcDetailedLevel"} and str(extra.get("emissions_category") or "") != "Offset":
        from services.project_context_helper import ProjectContextHelper

        jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, row.project_id)
        if key == "component":
            storage_sql = text('''
                SELECT COALESCE(g."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0)
                FROM activity_data ad LEFT JOIN v_grade2_component_level g
                  ON g."Jurisdiction" = :jurisdiction
                 AND g."Emissions Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '__no_match__')
                 AND g."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
                 AND g."Emissions Source" = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
                 AND g."UoM" = COALESCE(NULLIF(ad.extra_fields->>'unit_code', ''), '__no_match__')
                WHERE ad.id = :activity_id
                LIMIT 1
            ''')
        else:
            storage_sql = text('''
                SELECT COALESCE(g."Carbon Storage (tCO2e/UoM)", 0) * COALESCE(ad.quantity, 0)
                FROM activity_data ad LEFT JOIN v_grade34_detailed_level g
                  ON g."Jurisdiction" = :jurisdiction
                 AND g."Emissions Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_category', ''), '__no_match__')
                 AND g."Emissions Sub-Category" = COALESCE(NULLIF(ad.extra_fields->>'emissions_subcategory', ''), '__no_match__')
                 AND g."Emissions Source" = COALESCE(NULLIF(ad.extra_fields->>'emissions_source_name', ''), '__no_match__')
                 AND g."UoM" = COALESCE(NULLIF(ad.extra_fields->>'unit_code', ''), '__no_match__')
                WHERE ad.id = :activity_id
                LIMIT 1
            ''')
        stored_carbon = (await db.execute(storage_sql, {"jurisdiction": jurisdiction, "activity_id": row.id})).scalar_one_or_none()
        if stored_carbon is not None:
            await upsert_result(
                db,
                project_id=row.project_id,
                project_stage_instance_id=row.project_stage_instance_id,
                activity_data_id=row.id,
                value_key="stored_carbon",
                lifecycle_module_code=None,
                value=Decimal(str(stored_carbon)),
                unit_id=row.unit_id,
                source_category="Stored carbon",
                reporting_measure="stored_carbon",
            )

    if base in {"asset", "component", "constructionG2", "constructionG3", "recurringG3", "bcDetailedLevel", "concreteRegSimplified", "concreteRegDetailed"}:
        for field, module in (
            ("product_stage_a1_a3_tco2e", "A1-A3"),
            ("transport_stage_a4_tco2e", "A4"),
            ("construction_stage_a5_tco2e", "A5"),
        ):
            val = _number(extra.get(field))
            if val is not None:
                module_values.append((module, module, val, "common"))
        if not module_values:
            val = _number(extra.get("total_emissions_tco2e"))
            if val is not None:
                category = str(extra.get("emissions_category") or "")
                module = "Offsets" if category == "Offset" else (row.lifecycle_module_code or "A1-A3")
                module_values.append((module, module, val, "common"))
    elif base in {"componentRepl", "refurbishment", "replDetailed"}:
        val = _number(extra.get("total_emissions_tco2e"))
        if val is not None:
            module_values.append(("B2-5", "B2-5", val, "common"))
    elif base in {"useB1G2", "useB1G3"}:
        val = _number(extra.get("total_emissions_tco2e"))
        if val is not None:
            module_values.append(("B1", "B1", val, "common"))
    elif base == "opEnergy":
        for basis in ("location", "market"):
            val = _number(extra.get(f"{basis}_based_total_tco2e")) or _number(extra.get(f"{basis}_based_tco2e"))
            if val is not None:
                module_values.append((f"B6_{basis}", "B6", val, basis))
    elif base in {"electricity", "opEnergyElectricity"}:
        for basis in ("location", "market"):
            val = _number(extra.get(f"{basis}_based_tco2e"))
            if val is not None:
                module = "A5" if base == "electricity" else "B6"
                module_values.append((f"{module}_{basis}", module, val, basis))
    elif base == "opEnergyDetailed":
        val = _number(extra.get("total_emissions_tco2e"))
        if val is not None:
            category = str(extra.get("emissions_category") or "")
            module = "B7" if category == "Water" else "B6"
            module_values.append((module, module, val, "common"))
    elif base in {"roadUsers", "railUsers", "largeRailUsers", "largeRoadUsers", "largeRoadParams"}:
        field = (
            "relativeUserEmissions" if base == "roadUsers"
            else "total_emissions_tco2e" if base == "largeRoadUsers"
            else "emissions_total_ref_period_tco2e"
        )
        if base == "largeRoadParams":
            field = "final_user_emissions_tco2e"
        val = _number(extra.get(field) or extra.get("total_emissions_tco2e"))
        if val is not None:
            module_values.append(("B8", "B8", val, "common"))
    elif base == "shortcutSat4p":
        val = _number(extra.get("actual_scope3"))
        val4 = _number(extra.get("actual_scope4"))
        if val is not None or val4 is not None:
            source = str(extra.get("source") or "")
            module = (
                "A1-A3" if source == "Construction materials"
                else "A4" if source == "Transport (construction materials)"
                else "A5"
            )
            module_values.append((f"shortcut_actual_{module}", module, (val or Decimal(0)) + (val4 or Decimal(0)), "common"))

    if base == "shortcutIsMaterials":
        baseline = _number(extra.get("base_case"))
        actual = _number(extra.get("actual_case"))
        if actual is not None:
            module_values.append(("A1-A3", "A1-A3", actual, "common"))
        if baseline is not None and actual is not None:
            module_values.append(("baseline_adjustment", "A1-A3", max(Decimal(0), baseline - actual), "common"))
    elif base == "shortcutSat4p":
        baseline = (_number(extra.get("base_scope1")) or Decimal(0)) + (_number(extra.get("base_scope2")) or Decimal(0))
        actual = (_number(extra.get("actual_scope3")) or Decimal(0)) + (_number(extra.get("actual_scope4")) or Decimal(0))
        source = str(extra.get("source") or "")
        module = (
            "A1-A3" if source == "Construction materials"
            else "A4" if source == "Transport (construction materials)"
            else "A5"
        )
        module_values.append((f"baseline_adjustment_{module}", module, max(Decimal(0), baseline - actual), "common"))

    # Existing specialized calculators are authoritative when they already wrote
    # a result for the same module and accounting basis.
    from sqlalchemy import select
    existing_result_rows = (await db.execute(
        select(EmissionsResult).where(EmissionsResult.activity_data_id == row.id)
    )).scalars().all()
    existing_dimensions = {(r.lifecycle_module_code, r.accounting_basis) for r in existing_result_rows if not r.is_supplementary}
    for value_key, module, value, basis in module_values:
        is_offset = str(extra.get("emissions_category") or "") == "Offset"
        measure = (
            "baseline_adjustment"
            if value_key.startswith("baseline_adjustment") or value_key.startswith("upscaling_")
            else "actual" if value_key.startswith("shortcut_actual_")
            else "offset" if is_offset else None
        )
        if (module, basis) in existing_dimensions:
            # Baseline adjustments are separate facts and may share a module with gross values.
            if measure is None:
                continue
        await upsert_result(
            db,
            project_id=row.project_id,
            project_stage_instance_id=row.project_stage_instance_id,
            activity_data_id=row.id,
            value_key=value_key,
            lifecycle_module_code=None if measure == "offset" else module,
            value=value,
            unit_id=row.unit_id,
            accounting_basis=basis,
            reporting_measure=measure,
        )
        if measure is None:
            existing_dimensions.add((module, basis))

    # Preserve supplementary scope facts as first-class ledger entries.
    scope_fields = {
        "scope1": ("scope1_emissions_tco2e", "scope1"),
        "scope2": ("scope2_emissions_tco2e", "scope2"),
        "scope3": ("scope3_emissions_tco2e", "scope3"),
    }
    for key_name, (field, result_key) in scope_fields.items():
        val = _number(extra.get(field))
        if val is not None:
            await upsert_result(
                db,
                project_id=row.project_id,
                project_stage_instance_id=row.project_stage_instance_id,
                activity_data_id=row.id,
                value_key=result_key,
                lifecycle_module_code=None,
                is_supplementary=True,
                value=val,
                unit_id=row.unit_id,
                emissions_scope=key_name.removeprefix("scope"),
            )
    if base in {"railUsers", "largeRailUsers"}:
        await _persist_annual_rail_results(db, row, extra)
    return len(module_values)


async def _persist_annual_rail_results(db: AsyncSession, row: ActivityData, extra: dict) -> None:
    """Persist rail emissions per operating year when the activity is saved."""
    ref_period_value = _number(extra.get("emissions_total_ref_period_tco2e"))
    if ref_period_value is None or row.project_option_id is None:
        return
    project = await db.get(Project, row.project_id)
    if project is None or project.commencement_of_operations is None:
        return

    life = max(int(project.operational_life_years or 1), 1)
    annual_value = _number(extra.get("emissions_annual_tco2e"))
    if annual_value is None:
        annual_value = ref_period_value / Decimal(life)
    await db.execute(delete(EmissionsResult).where(
        EmissionsResult.project_option_id == row.project_option_id,
        EmissionsResult.activity_data_id.is_(None),
        EmissionsResult.assessment_year.is_not(None),
        EmissionsResult.lifecycle_module_code == "B8",
        EmissionsResult.value_key.op("~")(f"^b8_rail_{row.id.hex}_[0-9]+$"),
    ))
    revision = (await db.execute(text("""
        SELECT dataset_revision_id
        FROM project_dataset_revisions
        WHERE project_id = :project_id
        ORDER BY applied_at DESC, id DESC
        LIMIT 1
    """), {"project_id": str(row.project_id)})).scalar_one_or_none()

    for year in range(project.commencement_of_operations.year,
                       project.commencement_of_operations.year + life):
        stmt = pg_insert(EmissionsResult).values(
            project_id=row.project_id,
            project_stage_instance_id=row.project_stage_instance_id,
            project_option_id=row.project_option_id,
            assessment_year=year,
            activity_data_id=None,
            dataset_revision_id=revision,
            value_key=f"b8_rail_{row.id.hex}_{year}",
            lifecycle_module_code="B8",
            source_category="Rail user transport",
            accounting_basis="common",
            reporting_measure="actual",
            is_supplementary=False,
            value=annual_value,
            unit_id=row.unit_id,
        ).on_conflict_do_update(
            index_elements=[
                EmissionsResult.project_option_id,
                EmissionsResult.assessment_year,
                EmissionsResult.value_key,
            ],
            index_where=EmissionsResult.assessment_year.is_not(None),
            set_={"value": annual_value, "dataset_revision_id": revision},
        )
        await db.execute(stmt)
