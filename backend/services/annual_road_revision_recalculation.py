"""Rebuild specialist annual road emissions after a project dataset switch."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity_data import ActivityData
from models.emissions_results import EmissionsResult
from models.user_emissions_aus_large_road import UserEmissionsAusLargeRoadResult
from models.user_emissions_aus_small import UserEmissionsAusSmallResult
from models.user_emissions_nz import UserEmissionsNzResult
from models.user_emissions_nz_large_road import UserEmissionsNzLargeRoadResult


def _base_key(row: ActivityData) -> str:
    return (row.ui_table_key or "").split("-mitigation", 1)[0]


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _speed(row: ActivityData) -> Decimal | None:
    extra = row.extra_fields or {}
    speed = _decimal(extra.get("avg_speed") or extra.get("speed_kmh"))
    if speed is not None:
        return speed
    vkt = _decimal(extra.get("vkt")) or _decimal(row.quantity)
    vht = _decimal(extra.get("vht"))
    return vkt / vht if vkt is not None and vht else None


async def _clear_old_project_road_results(db: AsyncSession, project_id: UUID) -> None:
    for model in (
        UserEmissionsAusSmallResult,
        UserEmissionsAusLargeRoadResult,
        UserEmissionsNzResult,
        UserEmissionsNzLargeRoadResult,
    ):
        await db.execute(delete(model).where(model.project_id == project_id))
    await db.execute(
        delete(EmissionsResult).where(
            EmissionsResult.project_id == project_id,
            EmissionsResult.assessment_year.is_not(None),
            EmissionsResult.value_key.like("b8_road_%"),
        )
    )


async def _persist_road_facts(
    db: AsyncSession,
    *,
    option_id: UUID,
    project_class: str,
    is_nz: bool,
) -> None:
    from services.user_emissions_result_ledger import sync_annual_road_results

    await sync_annual_road_results(
        db,
        project_option_id=option_id,
        project_class=project_class,
        is_nz=is_nz,
    )


async def _mark_small_road_gaps(
    db: AsyncSession,
    *,
    option_id: UUID,
    inputs: list[ActivityData],
    is_nz: bool,
) -> list[dict[str, Any]]:
    model = UserEmissionsNzResult if is_nz else UserEmissionsAusSmallResult
    outputs = list((await db.execute(select(model).where(model.project_option_id == option_id))).scalars().all())
    input_by_vehicle = {
        str((row.extra_fields or {}).get("vehicle_type") or "").strip().casefold(): row
        for row in inputs
    }
    fields = (
        {
            "general fleet": ("general_fleet_intensity_gco2e_km", "general_fleet_emissions_tco2e"),
            "light vehicle": ("light_vehicle_intensity_gco2e_km", "light_vehicle_emissions_tco2e"),
            "heavy vehicle": ("heavy_vehicle_intensity_gco2e_km", "heavy_vehicle_emissions_tco2e"),
            "bus": ("bus_intensity_gco2e_km", "bus_emissions_tco2e"),
        }
        if is_nz else
        {
            "light vehicle": ("light_vehicle_intensity_gco2e_km", "light_vehicle_emissions_tco2e"),
            "medium vehicle": ("medium_vehicle_intensity_gco2e_km", "medium_vehicle_emissions_tco2e"),
            "heavy vehicle": ("heavy_vehicle_intensity_gco2e_km", "heavy_vehicle_emissions_tco2e"),
            "super heavy vehicle": ("super_heavy_vehicle_intensity_gco2e_km", "super_heavy_vehicle_emissions_tco2e"),
        }
    )
    missing: dict[str, dict[str, Any]] = {}
    emission_fields = [emission for _, emission in fields.values()]
    for output in outputs:
        for vehicle, (intensity_field, emission_field) in fields.items():
            source = input_by_vehicle.get(vehicle)
            if source is not None and getattr(output, intensity_field) is None:
                setattr(output, emission_field, Decimal("0"))
                missing[str(source.id)] = {
                    "activity_data_id": str(source.id),
                    "entry": vehicle.title(),
                    "data_entry_table": source.ui_table_key,
                    "dataset_table": "VEPM factors" if is_nz else "Australian road emission factors",
                    "message": "No emission factor was found for this vehicle and year in the selected dataset.",
                }
        output.total_annual_emissions_tco2e = sum(
            (getattr(output, field) or Decimal("0") for field in emission_fields),
            Decimal("0"),
        )
    await db.flush()
    return list(missing.values())


async def _mark_large_road_gaps(
    db: AsyncSession,
    *,
    option_id: UUID,
    inputs: list[ActivityData],
    is_nz: bool,
) -> list[dict[str, Any]]:
    model = UserEmissionsNzLargeRoadResult if is_nz else UserEmissionsAusLargeRoadResult
    outputs = list((await db.execute(select(model).where(model.project_option_id == option_id))).scalars().all())
    source_by_vehicle: dict[str, ActivityData] = {}
    for row in inputs:
        vehicle = str((row.extra_fields or {}).get("vehicle_type") or "").strip().casefold()
        if is_nz:
            vehicle = vehicle.replace(" ", "_")
        source_by_vehicle.setdefault(vehicle, row)
    missing: dict[str, dict[str, Any]] = {}
    for output in outputs:
        vehicle = str(output.vehicle_type).strip().casefold()
        if is_nz:
            vehicle = vehicle.replace(" ", "_")
        source = source_by_vehicle.get(vehicle)
        intensity_field = "emissions_intensity_gco2e_km" if is_nz else "emissions_intensity_gco2e_vkt"
        if source is not None and getattr(output, intensity_field) is None:
            output.emissions_tco2e = Decimal("0")
            missing[str(source.id)] = {
                "activity_data_id": str(source.id),
                "entry": str(output.vehicle_type),
                "data_entry_table": source.ui_table_key,
                "dataset_table": "VEPM factors" if is_nz else "Australian road emission factors",
                "message": f"No emission factor was found for {output.assessment_year} in the selected dataset.",
            }
    await db.flush()
    return list(missing.values())


async def recalculate_annual_road_results(
    db: AsyncSession,
    project_id: UUID,
) -> dict[str, list[dict[str, Any]]]:
    """Rebuild annual road result rows from saved road-user inputs.

    The source activity rows contain user VKT, speed and road parameters. Output
    rows and annual ledger facts are deleted first, inside the caller's pending
    project-revision transaction, so a technical failure rolls all of this back.
    """
    from crud.project import get_project

    project = await get_project(db, project_id)
    if project is None:
        return {"missing_data": [], "calculation_errors": []}
    class_value = getattr(project.project_class, "value", project.project_class)
    project_class = str(class_value).upper()
    from services.project_context_helper import ProjectContextHelper

    jurisdiction = await ProjectContextHelper.fetch_jurisdiction(db, project_id)
    is_nz = "new zealand" in jurisdiction.casefold() or jurisdiction.casefold() in {"nz", "nzl"}
    rows = list((await db.execute(
        select(ActivityData)
        .where(ActivityData.project_id == project_id)
        .order_by(ActivityData.created_at, ActivityData.id)
    )).scalars().all())
    # Specialist road results represent the project's primary user-emissions
    # inputs. Mitigation panel rows are recalculated through the activity ledger.
    base_rows = [row for row in rows if row.project_mitigation_id is None]
    small_rows = [row for row in base_rows if _base_key(row) == "roadUsers"]
    large_rows = [row for row in base_rows if _base_key(row) == "largeRoadUsers"]
    large_params = [row for row in base_rows if _base_key(row) == "largeRoadParams"]

    await _clear_old_project_road_results(db, project_id)
    missing: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if project_class != "LARGE":
        grouped: dict[tuple[UUID, UUID], dict[str, Any]] = {}
        for row in small_rows:
            if row.project_option_id is None:
                continue
            extra = row.extra_fields or {}
            vehicle = str(extra.get("vehicle_type") or "").strip().casefold()
            vkt = _decimal(extra.get("vkt")) or _decimal(row.quantity)
            speed = _speed(row)
            if not vehicle or vkt is None or speed is None:
                continue
            key = (row.project_stage_instance_id, row.project_option_id)
            payload = grouped.setdefault(key, {
                "project_id": project_id,
                "project_stage_instance_id": row.project_stage_instance_id,
                "project_option_id": row.project_option_id,
            })
            if is_nz:
                field = {
                    "general fleet": "general_fleet",
                    "light vehicle": "light_vehicle",
                    "heavy vehicle": "heavy_vehicle",
                    "bus": "bus",
                }.get(vehicle)
            else:
                field = {
                    "light vehicle": "light_vehicle",
                    "medium vehicle": "medium_vehicle",
                    "heavy vehicle": "heavy_vehicle",
                    "super heavy vehicle": "super_heavy_vehicle",
                }.get(vehicle)
            if field:
                payload[f"{field}_vkt"] = vkt
                payload[f"{field}_speed_kmh"] = speed

        for (stage_id, option_id), payload in grouped.items():
            try:
                if is_nz:
                    from schemas.user_emissions_nz import NzEmissionsCalculateRequest
                    from services.user_emissions_nz_calculations import calculate_and_store_nz

                    await calculate_and_store_nz(db, NzEmissionsCalculateRequest(**payload))
                else:
                    from schemas.user_emissions_aus_small import AusSmallEmissionsCalculateRequest
                    from services.user_emissions_aus_small_calculations import calculate_and_store_aus_small

                    await calculate_and_store_aus_small(db, AusSmallEmissionsCalculateRequest(**payload))
                missing.extend(await _mark_small_road_gaps(
                    db,
                    option_id=option_id,
                    inputs=[row for row in small_rows if row.project_stage_instance_id == stage_id and row.project_option_id == option_id],
                    is_nz=is_nz,
                ))
                await _persist_road_facts(
                    db, option_id=option_id, project_class=project_class, is_nz=is_nz
                )
            except Exception as exc:
                errors.append({
                    "activity_data_id": None,
                    "entry": "Road user emissions",
                    "data_entry_table": "roadUsers",
                    "message": str(exc),
                })

    else:
        user_groups: dict[tuple[UUID, UUID], list[ActivityData]] = {}
        param_by_group: dict[tuple[UUID, UUID], ActivityData] = {}
        for row in large_rows:
            if row.project_option_id is not None:
                user_groups.setdefault((row.project_stage_instance_id, row.project_option_id), []).append(row)
        for row in large_params:
            if row.project_option_id is not None:
                param_by_group.setdefault((row.project_stage_instance_id, row.project_option_id), row)

        for key, user_rows in user_groups.items():
            stage_id, option_id = key
            anchors: dict[int, list[dict[str, Any]]] = {}
            for row in user_rows:
                extra = row.extra_fields or {}
                year_raw = extra.get("modelled_year")
                vehicle = str(extra.get("vehicle_type") or "").strip()
                vkt = _decimal(extra.get("vkt")) or _decimal(row.quantity)
                speed = _speed(row)
                try:
                    year = int(year_raw)
                except (TypeError, ValueError):
                    continue
                if not vehicle or vkt is None or speed is None:
                    continue
                if is_nz:
                    vehicle = vehicle.casefold().replace(" ", "_")
                    anchor_vehicle = {"vehicle_type": vehicle, "vkt": vkt, "speed_kmh": speed}
                else:
                    anchor_vehicle = {"vehicle_type": vehicle, "vkt": vkt, "average_speed_kph": speed}
                anchors.setdefault(year, []).append(anchor_vehicle)
            if not anchors:
                continue
            payload: dict[str, Any] = {
                "project_id": project_id,
                "project_stage_instance_id": stage_id,
                "project_option_id": option_id,
                "anchor_years": [
                    {"year": year, "vehicles": vehicles}
                    for year, vehicles in sorted(anchors.items())
                ],
            }
            if not is_nz:
                params = (param_by_group.get(key).extra_fields or {}) if param_by_group.get(key) else {}
                payload.update({
                    "ev_uptake_scenario": params.get("ev_uptake_scenario") or "Step Change",
                    "roughness": params.get("roughness") or "Smooth",
                    "gradient": params.get("gradient") or "Flat",
                    "curvature": params.get("curvature") or "Straight",
                })
            try:
                if is_nz:
                    from schemas.user_emissions_nz_large_road import NzLargeRoadCalculateRequest
                    from services.user_emissions_nz_large_road_calculations import calculate_and_store_nz_large_road

                    await calculate_and_store_nz_large_road(db, NzLargeRoadCalculateRequest(**payload))
                else:
                    from schemas.user_emissions_aus_large_road import AusLargeRoadCalculateRequest
                    from services.user_emissions_aus_large_road_calculations import calculate_and_store_aus_large_road

                    await calculate_and_store_aus_large_road(db, AusLargeRoadCalculateRequest(**payload))
                missing.extend(await _mark_large_road_gaps(
                    db, option_id=option_id, inputs=user_rows, is_nz=is_nz
                ))
                await _persist_road_facts(
                    db, option_id=option_id, project_class=project_class, is_nz=is_nz
                )
            except Exception as exc:
                errors.append({
                    "activity_data_id": None,
                    "entry": "Road user emissions",
                    "data_entry_table": "largeRoadUsers",
                    "message": str(exc),
                })

    return {"missing_data": missing, "calculation_errors": errors}
