import logging
import uuid as _uuid
from typing import List, Optional, Type
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase
from core.base import Base

from models.background_grade_metrics import BackgroundGradeMetric
from models.base_case_assumptions import BaseCaseAssumption
from models.carbon_values import CarbonValue
from models.dataset_revisions import DatasetRevision
from models.default_transport_distances import DefaultTransportDistance
from models.default_waste_rates import DefaultWasteRate
from models.default_wastage_rate import DefaultWastageRate
from models.densities import Density
from models.electric_decarb_factors import ElectricDecarbFactor
from models.energy_density_conversions import EnergyDensityConversion
from models.electricity_recycling_assumption import ElectricityRecyclingAssumption
from models.ev_uptake_factors import EvUptakeFactor
from models.freight_rail_factors import FreightRailFactor
from models.fugitives import Fugitive
from models.maintenance_replacement_factors import MaintenanceReplacementFactor
from models.material_recycled_content import MaterialRecycledContent
from models.recycled_content_factors import RecycledContentFactor
from models.operational_equipment import OperationalEquipment
from models.concrete_mix_design import ConcreteMixAssumption, ConcreteMixDesign
from models.project_dataset_revisions import ProjectDatasetRevision
from models.emissions_factor_sets import EmissionsFactorSet
from models.vepm_factors import VepmFactor
from models.renewable_energy_classification import RenewableEnergyClassification
from schemas.dataset_revisions import DatasetRevisionCreate, DatasetRevisionUpdate

async def create_dataset_revision(db: AsyncSession, payload: DatasetRevisionCreate) -> DatasetRevision:
    obj = DatasetRevision(**payload.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_dataset_revision(db: AsyncSession, revision_id: UUID) -> Optional[DatasetRevision]:
    result = await db.execute(select(DatasetRevision).where(DatasetRevision.id == revision_id))
    return result.scalars().first()


async def get_dataset_revision_by_name(
    db: AsyncSession, name: str,
    scope_type: str = "DEFAULT",
    scope_id: Optional[UUID] = None,
) -> Optional[DatasetRevision]:
    q = select(DatasetRevision).where(
        DatasetRevision.name == name,
        DatasetRevision.scope_type == scope_type,
    )
    if scope_id is not None:
        q = q.where(DatasetRevision.scope_id == scope_id)
    else:
        q = q.where(DatasetRevision.scope_id.is_(None))
    result = await db.execute(q)
    return result.scalars().first()


async def get_published_dataset_revision(db: AsyncSession) -> Optional[DatasetRevision]:
    result = await db.execute(
        select(DatasetRevision)
        .where(
            DatasetRevision.status == "published",
            DatasetRevision.scope_type == "DEFAULT",
            DatasetRevision.scope_id.is_(None),
        )
        .order_by(DatasetRevision.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def list_dataset_revisions(
    db: AsyncSession,
    status: Optional[str] = None,
    scope_type: Optional[str] = None,
    scope_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DatasetRevision]:
    q = select(DatasetRevision)
    if status is not None:
        q = q.where(DatasetRevision.status == status)
    if scope_type is not None:
        q = q.where(DatasetRevision.scope_type == scope_type)
        if scope_id is not None:
            q = q.where(DatasetRevision.scope_id == scope_id)
        else:
            if scope_type == "DEFAULT":
                q = q.where(DatasetRevision.scope_id.is_(None))
    q = q.order_by(DatasetRevision.name).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def update_dataset_revision(
    db: AsyncSession, obj: DatasetRevision, payload: DatasetRevisionUpdate
) -> DatasetRevision:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_dataset_revision(db: AsyncSession, revision_id: UUID) -> bool:
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        return False
    await db.delete(obj)
    return True


async def count_bound_projects(db: AsyncSession, revision_id: UUID) -> int:
    result = await db.execute(
        select(ProjectDatasetRevision).where(
            ProjectDatasetRevision.dataset_revision_id == revision_id
        )
    )
    return len(result.scalars().all())


async def set_revision_status(
    db: AsyncSession, obj: DatasetRevision, new_status: str
) -> DatasetRevision:
    obj.status = new_status
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def branch_dataset_revision(
    db: AsyncSession,
    source_id: UUID,
    name: str,
    notes: Optional[str] = None,
    created_by: Optional[UUID] = None,
    scope_type: str = "DEFAULT",
    scope_id: Optional[UUID] = None,
) -> DatasetRevision:
    
    new_rev = DatasetRevision(
        id=_uuid.uuid4(),
        name=name,
        notes=notes,
        status="draft",
        scope_type=scope_type,
        scope_id=scope_id,
        created_by=created_by,
        parent_revision_id=source_id,
    )
    db.add(new_rev)
    await db.flush()
    await db.refresh(new_rev)

    async def _copy_table_bulk(model: Type[DeclarativeBase], table_name: str):
        # ORM mappings can outlive columns removed by the active migration
        # lineage. Reflect the live table so a stale mapped attribute does not
        # make an otherwise valid branch fail (or omit live database fields).
        revision_column = await db.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name = 'dataset_revision_id'
        """), {"table_name": table_name})
        if revision_column.scalar_one_or_none() is None:
            raise RuntimeError(
                f"Cannot branch dataset table '{table_name}': "
                "dataset_revision_id is missing from the database schema"
            )

        result = await db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name NOT IN ('id', 'dataset_revision_id')
              AND is_generated = 'NEVER'
              AND is_identity = 'NO'
            ORDER BY ordinal_position
        """), {"table_name": table_name})
        columns = list(result.scalars().all())
        if not columns:
            # Tables containing only their key columns have nothing to clone.
            return

        quoted_table = '"' + table_name.replace('"', '""') + '"'
        columns_str = ", ".join('"' + column.replace('"', '""') + '"' for column in columns)
        insert_sql = text(f"""
            INSERT INTO {quoted_table} (id, dataset_revision_id, {columns_str})
            SELECT gen_random_uuid(), :new_rev_id, {columns_str}
            FROM {quoted_table}
            WHERE dataset_revision_id = :source_id
        """)

        await db.execute(insert_sql, {"new_rev_id": new_rev.id, "source_id": source_id})

    # Clone every mapped table owned by a revision. Exclude bindings, audit
    # records, and project/user activity; those are not dataset contents.
    excluded_tables = {
        "project_dataset_revisions",
        "dataset_revision_changes",
        "activity_data",
        "user_emissions_nz_large_road",
        # Removed by 9a8b7c6d5e4f: the active revision architecture stores
        # dataset deltas directly and no longer has factor-set rows to clone.
        "emissions_factor_sets",
    }
    mapped_models = {
        mapper.class_ for mapper in Base.registry.mappers
        if "dataset_revision_id" in mapper.local_table.c
        and mapper.local_table.name not in excluded_tables
    }
    for model in sorted(mapped_models, key=lambda item: item.__tablename__):
        await _copy_table_bulk(model, model.__tablename__)
    
    await db.refresh(new_rev)
    return new_rev
