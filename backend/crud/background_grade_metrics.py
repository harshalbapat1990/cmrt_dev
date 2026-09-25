from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.background_grade_metrics import BackgroundGradeMetric
from models.benchmark_mastertypes import BenchmarkMastertype
from models.benchmark_typecasts import BenchmarkTypecast
from models.emissions_categories_new import EmissionsCategoryRecord
from models.ghg_scopes import GhgScope
from models.grade_definitions import GradeDefinition
from models.jurisdictions import Jurisdiction
from models.lifecycle_modules import LifecycleModule
from models.metric_types import MetricType
from models.units import Unit
from schemas.background_grade_metrics import (
    BackgroundGradeMetricCreate,
    BackgroundGradeMetricUpdate,
)

EC = aliased(EmissionsCategoryRecord, name="ec")
ESC = aliased(EmissionsCategoryRecord, name="esc")


def _joined_query():
    return (
        select(
            BackgroundGradeMetric,
            GradeDefinition.name.label("grade_name"),
            Jurisdiction.name.label("jurisdiction_name"),
            BenchmarkMastertype.name.label("mastertype_name"),
            BenchmarkTypecast.name.label("typecast_name"),
            EC.name.label("emissions_category"),
            ESC.name.label("emissions_subcategory"),
            LifecycleModule.name.label("lifecycle_module_name"),
            GhgScope.name.label("ghg_scope_name"),
            MetricType.code.label("metric_type_code"),
            MetricType.name.label("metric_type_name"),
            Unit.code.label("unit_code"),
            Unit.label.label("unit_label"),
        )
        .outerjoin(GradeDefinition, GradeDefinition.id == BackgroundGradeMetric.grade_id)
        .outerjoin(Jurisdiction, Jurisdiction.id == BackgroundGradeMetric.jurisdiction_id)
        .outerjoin(BenchmarkMastertype, BenchmarkMastertype.id == BackgroundGradeMetric.mastertype_id)
        .outerjoin(BenchmarkTypecast, BenchmarkTypecast.id == BackgroundGradeMetric.typecast_id)
        .outerjoin(EC, EC.id == BackgroundGradeMetric.emissions_category_id)
        .outerjoin(ESC, ESC.id == BackgroundGradeMetric.emissions_subcategory_id)
        .outerjoin(LifecycleModule, LifecycleModule.code == BackgroundGradeMetric.lifecycle_module_code)
        .outerjoin(GhgScope, GhgScope.id == BackgroundGradeMetric.ghg_scope_id)
        .outerjoin(MetricType, MetricType.id == BackgroundGradeMetric.metric_type_id)
        .outerjoin(Unit, Unit.id == BackgroundGradeMetric.unit_id)
    )


def _row_to_dict(row) -> Dict[str, Any]:
    bgm: BackgroundGradeMetric = row[0]
    return {
        "id": bgm.id,
        "dataset_revision_id": bgm.dataset_revision_id,
        "grade_id": bgm.grade_id,
        "jurisdiction_id": bgm.jurisdiction_id,
        "mastertype_id": bgm.mastertype_id,
        "typecast_id": bgm.typecast_id,
        "emissions_category_id": bgm.emissions_category_id,
        "emissions_subcategory_id": bgm.emissions_subcategory_id,
        "emissions_source": bgm.emissions_source,
        "lifecycle_module_code": bgm.lifecycle_module_code,
        "ghg_scope_id": bgm.ghg_scope_id,
        "metric_type_id": bgm.metric_type_id,
        "band_code": bgm.band_code,
        "unit_id": bgm.unit_id,
        "value": bgm.value,
        "assumed_quantity_default": bgm.assumed_quantity_default,
        "source": bgm.source,
        "is_active": bgm.is_active,
        "created_at": bgm.created_at,
        "grade_name": row.grade_name,
        "jurisdiction_name": row.jurisdiction_name,
        "mastertype_name": row.mastertype_name,
        "typecast_name": row.typecast_name,
        "emissions_category": row.emissions_category,
        "emissions_subcategory": row.emissions_subcategory,
        "lifecycle_module_name": row.lifecycle_module_name,
        "ghg_scope_name": row.ghg_scope_name,
        "metric_type_code": row.metric_type_code,
        "metric_type_name": row.metric_type_name,
        "unit_code": row.unit_code,
        "unit_label": row.unit_label,
    }


# ---------------------------------------------------------------------------
# Activity-data metric natural-key support
# ---------------------------------------------------------------------------
# These are the stable fields that identify one background-grade-metric row
# inside a dataset revision. The BGM primary key is deliberately excluded
# because revision cloning creates a new metric UUID.
_BGM_NATURAL_KEY_FIELDS = (
    "grade_id",
    "jurisdiction_id",
    "mastertype_id",
    "typecast_id",
    "emissions_category_id",
    "emissions_subcategory_id",
    "emissions_source",
    "lifecycle_module_code",
    "ghg_scope_id",
    "metric_type_id",
    "band_code",
    "unit_id",
)

_BGM_UUID_KEY_FIELDS = frozenset({
    "jurisdiction_id",
    "mastertype_id",
    "typecast_id",
    "emissions_category_id",
    "emissions_subcategory_id",
    "metric_type_id",
    "unit_id",
})

_BGM_INT_KEY_FIELDS = frozenset({"grade_id", "ghg_scope_id"})


def background_grade_metric_to_natural_key(metric: BackgroundGradeMetric) -> Dict[str, Any]:
    """Build the canonical JSON-safe key persisted on ActivityData."""
    key: Dict[str, Any] = {}
    for field in _BGM_NATURAL_KEY_FIELDS:
        value = getattr(metric, field, None)
        if value is not None and field in _BGM_UUID_KEY_FIELDS:
            value = str(value)
        key[field] = value
    return key


def _coerce_natural_key_value(field: str, value: Any) -> Any:
    if value is None:
        return None
    if field in _BGM_UUID_KEY_FIELDS:
        return UUID(str(value))
    if field in _BGM_INT_KEY_FIELDS:
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


async def get_background_grade_metric_by_natural_key(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID],
    natural_key: Optional[Dict[str, Any]],
) -> Optional[BackgroundGradeMetric]:
    """Resolve one active BGM row from the canonical ActivityData natural key.

    The lookup is exact across all identity fields. An ambiguous match is treated
    as unresolved rather than selecting an arbitrary emission factor.
    """
    if not natural_key:
        return None

    missing = [field for field in _BGM_NATURAL_KEY_FIELDS if field not in natural_key]
    if missing:
        return None

    q = select(BackgroundGradeMetric).where(
        BackgroundGradeMetric.is_active.is_(True),
    )
    if dataset_revision_id is None:
        q = q.where(BackgroundGradeMetric.dataset_revision_id.is_(None))
    else:
        q = q.where(BackgroundGradeMetric.dataset_revision_id == dataset_revision_id)

    try:
        for field in _BGM_NATURAL_KEY_FIELDS:
            column = getattr(BackgroundGradeMetric, field)
            value = _coerce_natural_key_value(field, natural_key[field])
            if value is None:
                q = q.where(column.is_(None))
            else:
                q = q.where(column == value)
    except (TypeError, ValueError) as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Invalid background-grade-metric natural key: %r (%s)", natural_key, exc
        )
        return None

    rows = (await db.execute(q.limit(2))).scalars().all()
    if len(rows) != 1:
        if len(rows) > 1:
            import logging
            logging.getLogger(__name__).warning(
                "Ambiguous background-grade-metric natural key for revision %s: %r",
                dataset_revision_id,
                natural_key,
            )
        return None
    return rows[0]


async def create_background_grade_metric(
    db: AsyncSession, payload: BackgroundGradeMetricCreate
) -> BackgroundGradeMetric:
    obj = BackgroundGradeMetric(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_background_grade_metric(
    db: AsyncSession, metric_id: UUID
) -> Optional[Dict[str, Any]]:
    q = _joined_query().where(BackgroundGradeMetric.id == metric_id)
    result = await db.execute(q)
    row = result.first()
    return _row_to_dict(row) if row is not None else None


async def get_background_grade_metric_orm(
    db: AsyncSession, metric_id: UUID
) -> Optional[BackgroundGradeMetric]:
    result = await db.execute(
        select(BackgroundGradeMetric).where(BackgroundGradeMetric.id == metric_id)
    )
    return result.scalars().first()


async def list_background_grade_metrics(
    db: AsyncSession,
    dataset_revision_id: Optional[UUID] = None,
    dataset_revision_ids: List[UUID] = [],
    grade_id: Optional[int] = None,
    jurisdiction_name: Optional[str] = None,
    jurisdiction_names: List[str] = [],
    mastertype_id: Optional[UUID] = None,
    typecast_id: Optional[UUID] = None,
    band_code: Optional[str] = None,
    emissions_category_id: Optional[UUID] = None,
    emissions_subcategory_id: Optional[UUID] = None,
    emissions_categories: List[str] = [],
    emissions_subcategories: List[str] = [],
    emissions_source: Optional[str] = None,
    lifecycle_module_code: Optional[str] = None,
    unit_codes: List[str] = [],
    metric_type_codes: List[str] = [],
    skip: int = 0,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    q = _joined_query()
    if dataset_revision_ids:
        q = q.where(BackgroundGradeMetric.dataset_revision_id.in_(dataset_revision_ids))
    elif dataset_revision_id is not None:
        q = q.where(BackgroundGradeMetric.dataset_revision_id == dataset_revision_id)
    if grade_id is not None:
        q = q.where(BackgroundGradeMetric.grade_id == grade_id)
    q = q.where(BackgroundGradeMetric.is_active.is_(True))
    if jurisdiction_name is not None:
        q = q.where(Jurisdiction.name == jurisdiction_name)
    if jurisdiction_names:
        q = q.where(Jurisdiction.name.in_(jurisdiction_names))
    if mastertype_id is not None:
        q = q.where(BackgroundGradeMetric.mastertype_id == mastertype_id)
    if typecast_id is not None:
        q = q.where(BackgroundGradeMetric.typecast_id == typecast_id)
    if band_code is not None:
        q = q.where(BackgroundGradeMetric.band_code == band_code)
    if emissions_category_id is not None:
        q = q.where(BackgroundGradeMetric.emissions_category_id == emissions_category_id)
    if emissions_subcategory_id is not None:
        q = q.where(BackgroundGradeMetric.emissions_subcategory_id == emissions_subcategory_id)
    if emissions_categories:
        q = q.where(EC.name.in_(emissions_categories))
    if emissions_subcategories:
        q = q.where(ESC.name.in_(emissions_subcategories))
    if emissions_source:
        q = q.where(BackgroundGradeMetric.emissions_source.ilike(f"%{emissions_source}%"))
    if lifecycle_module_code is not None:
        q = q.where(BackgroundGradeMetric.lifecycle_module_code == lifecycle_module_code)
    if unit_codes:
        q = q.where(Unit.code.in_(unit_codes))
    if metric_type_codes:
        q = q.where(MetricType.code.in_(metric_type_codes))
    q = q.order_by(
        BackgroundGradeMetric.grade_id,
        BackgroundGradeMetric.mastertype_id,
        BackgroundGradeMetric.typecast_id,
        BackgroundGradeMetric.lifecycle_module_code,
    ).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_row_to_dict(row) for row in result.all()]


async def update_background_grade_metric(
    db: AsyncSession, obj: BackgroundGradeMetric, payload: BackgroundGradeMetricUpdate
) -> BackgroundGradeMetric:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def supersede_background_grade_metric(
    db: AsyncSession,
    old_obj: BackgroundGradeMetric,
    payload: dict,
) -> BackgroundGradeMetric:
    old_obj.is_active = False
    db.add(old_obj)
    skip_cols = {"id", "is_active", "created_at"}
    data = {
        c.name: getattr(old_obj, c.name)
        for c in BackgroundGradeMetric.__table__.columns
        if c.name not in skip_cols
    }
    data.update(payload)
    new_obj = BackgroundGradeMetric(**data, is_active=True)
    db.add(new_obj)
    await db.flush()
    await db.refresh(new_obj)
    return new_obj


async def delete_background_grade_metric(db: AsyncSession, metric_id: UUID) -> bool:
    obj = await get_background_grade_metric_orm(db, metric_id)
    if not obj:
        return False
    await db.delete(obj)
    return True
