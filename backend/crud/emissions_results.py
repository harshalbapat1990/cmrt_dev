from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.emissions_results import EmissionsResult
from models.activity_data import ActivityData


def _label(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("label") or value.get("name") or value.get("value")
    return str(value).strip() or None


def _reporting_dimensions(row: Optional[ActivityData], value_key: str) -> dict:
    if row is None:
        return {
            "source_category": None,
            "emissions_scope": value_key.removeprefix("scope").split("_", 1)[0] if value_key.startswith("scope") else None,
            "accounting_basis": "market" if "market" in value_key else "location" if "location" in value_key else "common",
            "reporting_measure": "actual",
        }
    extra = row.extra_fields or {}
    key = row.ui_table_key or ""
    base_key = key.split("-mitigation", 1)[0]
    category = _label(extra.get("emissions_category"))
    if not category:
        if "electricity" in base_key.lower():
            category = "Electricity"
        elif base_key in {"asset", "component", "constructionG2", "constructionG3", "bcDetailedLevel"}:
            category = "Materials"
    scope = None
    if value_key.startswith("scope"):
        scope = value_key.removeprefix("scope").split("_", 1)[0]
    elif value_key.startswith("scope") is False and value_key in {"A1-A3", "A4", "A5", "B1", "B2-5", "B6", "B7", "B8"}:
        scope = None
    basis = "market" if "market" in value_key else "location" if "location" in value_key else "common"
    measure = "mitigation" if row.project_mitigation_id or "-mitigation" in key else "actual"
    if _label(extra.get("emissions_category")) == "Offset":
        measure = "offset"
    return {
        "source_category": category,
        "emissions_scope": scope,
        "accounting_basis": basis,
        "reporting_measure": measure,
    }


async def upsert_result(
    db: AsyncSession,
    *,
    project_id: UUID,
    project_stage_instance_id: UUID,
    activity_data_id: UUID,
    value_key: str,
    lifecycle_module_code: Optional[str] = None,
    is_supplementary: bool = False,
    value: Decimal,
    unit_id: Optional[UUID] = None,
    source_category: Optional[str] = None,
    emissions_scope: Optional[str] = None,
    accounting_basis: Optional[str] = None,
    reporting_measure: Optional[str] = None,
) -> EmissionsResult:
    activity = await db.get(ActivityData, activity_data_id)
    dims = _reporting_dimensions(activity, value_key)
    dims.update({
        name: val for name, val in {
            "source_category": source_category,
            "emissions_scope": emissions_scope,
            "accounting_basis": accounting_basis,
            "reporting_measure": reporting_measure,
        }.items() if val is not None
    })
    stmt = (
        pg_insert(EmissionsResult)
        .values(
            project_id=project_id,
            project_stage_instance_id=project_stage_instance_id,
            activity_data_id=activity_data_id,
            value_key=value_key,
            lifecycle_module_code=lifecycle_module_code,
            is_supplementary=is_supplementary,
            **dims,
            value=value,
            unit_id=unit_id,
        )
        .on_conflict_do_update(
            constraint="emissions_results_activity_value_key",
            set_={
                "value": value,
                "unit_id": unit_id,
                "lifecycle_module_code": lifecycle_module_code,
                **dims,
            },
        )
        .returning(EmissionsResult)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.scalars().first()


async def list_results_for_stage(
    db: AsyncSession,
    stage_instance_id: UUID,
) -> List[EmissionsResult]:
    q = select(EmissionsResult).where(
        EmissionsResult.project_stage_instance_id == stage_instance_id
    )
    result = await db.execute(q)
    return result.scalars().all()


async def list_results_for_activity(
    db: AsyncSession,
    activity_data_id: UUID,
) -> List[EmissionsResult]:
    q = select(EmissionsResult).where(EmissionsResult.activity_data_id == activity_data_id)
    result = await db.execute(q)
    return result.scalars().all()
