
# app/routers/lookup.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from core.config import Settings
from core.session import get_session
from core.security import get_current_principal, Principal
from models.organizations import Organization

from models.background_grade_metrics import BackgroundGradeMetric
from models.units import Unit
from models.emissions_categories_new import EmissionsCategoryRecord
from models.lookup_data import EmissionSource, EmissionFactor, EmissionFactorValue
from crud.unit_conversions import build_unit_options_with_conversions
from schemas.lookup_data import (
    UnitOut, UnitOptionOut,
    EmissionSourceOut, EmissionFactorOut, EmissionFactorValueOut,
    EmissionFactorWithValuesOut,
    BgmItemOut, BgmSourceOut,
)

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

# --------------------------
# Units (GET only)
# --------------------------
@router.get("/units", response_model=List[UnitOut])
async def list_units(
    q: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Unit)
    if q:
        stmt = stmt.where(func.lower(Unit.code).like(f"%{q.lower()}%"))
    stmt = stmt.order_by(Unit.code).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [UnitOut(id=r.id, name=r.code) for r in rows]

@router.get("/units/{id}", response_model=UnitOut)
async def get_unit(id: UUID, db: AsyncSession = Depends(get_session)):
    stmt = select(Unit).where(Unit.id == id)
    u = (await db.execute(stmt)).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Unit not found")
    return UnitOut(id=u.id, name=u.code)

# ----------------------------------------------------------
# Units available for electricity tables (MWh canonical +
# all units that convert to MWh via unit_conversions)
# ----------------------------------------------------------
@router.get("/electricity-units", response_model=List[UnitOptionOut])
async def list_electricity_units(db: AsyncSession = Depends(get_session)):
    """Return only Wh, kWh, MWh and GWh for electricity tables."""

    stmt = select(Unit).where(func.lower(Unit.code) == "mwh")
    mwh_unit = (await db.execute(stmt)).scalar_one_or_none()

    if not mwh_unit:
        return []

    options = await build_unit_options_with_conversions(
        db,
        [mwh_unit.id]
    )

    allowed_units = {"wh", "kwh", "mwh", "gwh"}

    return [
        option
        for option in options
        if option["name"].lower() in allowed_units
    ]

# ----------------------------------------------------------
# Units available for a given typecast (via BGM rows)
# ----------------------------------------------------------
@router.get("/benchmark-typecasts/{id}/units", response_model=List[UnitOptionOut])
async def list_units_for_typecast(
    id: UUID,
    grade_ids: Optional[str] = Query(None, description="Comma-separated grade IDs to filter by, e.g. '1'"),
    db: AsyncSession = Depends(get_session),
):
    bgm = BackgroundGradeMetric
    u = Unit
    stmt = (
        select(distinct(u.id))
        .join(bgm, bgm.unit_id == u.id)
        .where(bgm.typecast_id == id)
    )
    if grade_ids:
        grade_id_list = [int(g.strip()) for g in grade_ids.split(",") if g.strip().isdigit()]
        if grade_id_list:
            stmt = stmt.where(bgm.grade_id.in_(grade_id_list))
    canonical_ids = [r[0] for r in (await db.execute(stmt)).all()]
    return await build_unit_options_with_conversions(db, canonical_ids)

# -----------------------------------------------------------------------
# BGM-grade-filtered lookups (used by G2 / G3+4 data-entry dropdowns)
# -----------------------------------------------------------------------
@router.get("/bgm-categories", response_model=List[BgmItemOut])
async def list_bgm_categories(
    grade_ids: str = Query(...),
    project_id: Optional[UUID] = Query(None),
    use_org_jurisdiction: bool = Query(False),
    current_user: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    """Distinct top-level emissions categories that have BGM rows for the given grades."""
    grade_id_list = [int(g.strip()) for g in grade_ids.split(",") if g.strip().isdigit()]
    ec = EmissionsCategoryRecord
    bgm = BackgroundGradeMetric
    stmt = (
        select(distinct(ec.id), ec.name)
        .join(bgm, bgm.emissions_category_id == ec.id)
        .where(bgm.grade_id.in_(grade_id_list))
        .where(ec.parent_category_id.is_(None))
        .order_by(ec.name)
    )
    # Note: jurisdiction filtering requires the Alembic migration to have been applied
    # If migration hasn't run yet, this filter is skipped and all categories are returned
    if project_id:
        try:
            from crud.project import get_jurisdiction_name_for_project
            from models.jurisdictions import Jurisdiction
            jurisdiction_name = await get_jurisdiction_name_for_project(db, project_id)
            if jurisdiction_name:
                jur_result = await db.execute(
                    select(Jurisdiction.id).where(Jurisdiction.name == jurisdiction_name)
                )
                jurisdiction_id = jur_result.scalar_one_or_none()
                if jurisdiction_id:
                    stmt = stmt.where(bgm.jurisdiction_id == jurisdiction_id)
        except Exception as e:
            # Handle case where jurisdiction_id column doesn't exist yet (migration not applied)
            # Rollback to clear failed transaction state, then continue without jurisdiction filter
            import logging
            logging.warning(f"Failed to filter by project jurisdiction (migration may not be applied): {str(e)}")
            await db.rollback()
            # Continue without jurisdiction filter - return all categories for the grades
    if use_org_jurisdiction and current_user.organization_id:
        org_result = await db.execute(
            select(Organization.jurisdiction_id)
            .where(Organization.id == current_user.organization_id)
        )
        org_jurisdiction_id = org_result.scalar_one_or_none()
        if org_jurisdiction_id:
            stmt = stmt.where(
                bgm.jurisdiction_id == org_jurisdiction_id
            )
    rows = (await db.execute(stmt)).all()
    return [BgmItemOut(id=r[0], name=r[1]) for r in rows]


@router.get("/bgm-subcategories", response_model=List[BgmItemOut])
async def list_bgm_subcategories(
    grade_ids: str = Query(..., description="Comma-separated grade IDs"),
    category_id: UUID = Query(..., description="Parent emissions category UUID"),
    project_id: Optional[UUID] = Query(None, description="Filter by the project's jurisdiction"),
    use_org_jurisdiction: bool = Query(False),
    current_user: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    """Distinct subcategories (children of category_id) that have BGM rows for the given grades."""
    grade_id_list = [int(g.strip()) for g in grade_ids.split(",") if g.strip().isdigit()]
    ec = EmissionsCategoryRecord
    bgm = BackgroundGradeMetric
    stmt = (
        select(distinct(ec.id), ec.name)
        .join(bgm, bgm.emissions_subcategory_id == ec.id)
        .where(bgm.grade_id.in_(grade_id_list))
        .where(bgm.emissions_category_id == category_id)
        .order_by(ec.name)
    )
    # Note: jurisdiction filtering requires the Alembic migration to have been applied
    # If migration hasn't run yet, this filter is skipped and all subcategories are returned
    if project_id:
        try:
            from crud.project import get_jurisdiction_name_for_project
            from models.jurisdictions import Jurisdiction
            jurisdiction_name = await get_jurisdiction_name_for_project(db, project_id)
            if jurisdiction_name:
                jur_result = await db.execute(
                    select(Jurisdiction.id).where(Jurisdiction.name == jurisdiction_name)
                )
                jurisdiction_id = jur_result.scalar_one_or_none()
                if jurisdiction_id:
                    stmt = stmt.where(bgm.jurisdiction_id == jurisdiction_id)
        except Exception as e:
            # Handle case where jurisdiction_id column doesn't exist yet (migration not applied)
            # Rollback to clear failed transaction state, then continue without jurisdiction filter
            import logging
            logging.warning(f"Failed to filter by project jurisdiction (migration may not be applied): {str(e)}")
            await db.rollback()
            # Continue without jurisdiction filter - return all subcategories for the grades
    if use_org_jurisdiction and current_user.organization_id:
        org_result = await db.execute(
            select(Organization.jurisdiction_id)
            .where(Organization.id == current_user.organization_id)
        )
        org_jurisdiction_id = org_result.scalar_one_or_none()
        if org_jurisdiction_id:
            stmt = stmt.where(
                bgm.jurisdiction_id == org_jurisdiction_id
            )
    rows = (await db.execute(stmt)).all()
    return [BgmItemOut(id=r[0], name=r[1]) for r in rows]


@router.get("/bgm-sources", response_model=List[BgmSourceOut])
async def list_bgm_sources(
    grade_ids: str = Query(..., description="Comma-separated grade IDs"),
    subcategory_id: UUID = Query(..., description="Emissions subcategory UUID"),
    project_id: Optional[UUID] = Query(
        None,
        description="Filter by the project's jurisdiction"
    ),
    use_org_jurisdiction: bool = Query(False),
    current_user: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_session),
):
    """Distinct emissions_source strings from BGM for the given grades and subcategory."""
    
    grade_id_list = [
        int(g.strip())
        for g in grade_ids.split(",")
        if g.strip().isdigit()
    ]

    bgm = BackgroundGradeMetric

    stmt = (
        select(distinct(bgm.emissions_source))
        .where(bgm.grade_id.in_(grade_id_list))
        .where(bgm.emissions_subcategory_id == subcategory_id)
        .where(bgm.emissions_source.isnot(None))
        .order_by(bgm.emissions_source)
    )

    # Note: jurisdiction filtering requires the Alembic migration to have been applied
    # If migration hasn't run yet, this filter is skipped and all sources are returned
    if project_id:
        try:
            from crud.project import get_jurisdiction_name_for_project
            from models.jurisdictions import Jurisdiction

            jurisdiction_name = await get_jurisdiction_name_for_project(
                db,
                project_id
            )

            if jurisdiction_name:
                jur_result = await db.execute(
                    select(Jurisdiction.id).where(
                        Jurisdiction.name == jurisdiction_name
                    )
                )

                jurisdiction_id = jur_result.scalar_one_or_none()

                if jurisdiction_id:
                    stmt = stmt.where(
                        bgm.jurisdiction_id == jurisdiction_id
                    )

        except Exception as e:
            import logging

            logging.warning(
                f"Failed to filter by project jurisdiction "
                f"(migration may not be applied): {str(e)}"
            )

            await db.rollback()

            # Continue without jurisdiction filter
    if use_org_jurisdiction and current_user.organization_id:
        org_result = await db.execute(
            select(Organization.jurisdiction_id)
            .where(Organization.id == current_user.organization_id)
        )
        org_jurisdiction_id = org_result.scalar_one_or_none()
        if org_jurisdiction_id:
            stmt = stmt.where(
                bgm.jurisdiction_id == org_jurisdiction_id
            )
    rows = (await db.execute(stmt)).scalars().all()

    return [
        BgmSourceOut(id=r, name=r)
        for r in rows
        if r
    ]


@router.get("/bgm-source-units", response_model=List[UnitOptionOut])
async def list_bgm_source_units(
    grade_ids: str = Query(..., description="Comma-separated grade IDs"),
    subcategory_id: UUID = Query(..., description="Emissions subcategory UUID"),
    source: str = Query(..., description="Emissions source string"),
    dataset_revision_id: Optional[UUID] = Query(None, description="Active dataset revision UUID"),
    db: AsyncSession = Depends(get_session),
):
    """Distinct units from BGM for the given grades, subcategory and emissions source string,
    plus any units reachable via unit_conversions from those canonical units."""
    grade_id_list = [int(g.strip()) for g in grade_ids.split(",") if g.strip().isdigit()]
    bgm = BackgroundGradeMetric
    stmt = (
        select(distinct(bgm.unit_id))
        .where(bgm.grade_id.in_(grade_id_list))
        .where(bgm.emissions_subcategory_id == subcategory_id)
        .where(bgm.emissions_source == source)
        .where(bgm.unit_id.isnot(None))
    )
    canonical_ids = [r[0] for r in (await db.execute(stmt)).all()]
    return await build_unit_options_with_conversions(db, canonical_ids, dataset_revision_id)

# -----------------------------------------------------------------------
# Emission Sources (GET) - filtered by sub-category
# -----------------------------------------------------------------------
@router.get("/emission-sources", response_model=List[EmissionSourceOut])
async def list_emission_sources(
    emissions_sub_category_id: Optional[UUID] = Query(None),
    skip: int = 0,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
):
    es = EmissionSource
    u = Unit
    stmt = (
        select(es, u.code.label("unit_name"))
        .outerjoin(u, es.measurement_unit_id == u.id)
    )
    if emissions_sub_category_id:
        stmt = stmt.where(es.emissions_sub_category_id == emissions_sub_category_id)
    stmt = stmt.where(es.is_active == True).order_by(es.name).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).all()
    return [EmissionSourceOut(
        id=r[0].id,
        name=r[0].name,
        emissions_sub_category_id=r[0].emissions_sub_category_id,
        measurement_unit_id=r[0].measurement_unit_id,
        measurement_unit_name=r[1],
        is_active=r[0].is_active,
        created_on=r[0].created_on,
        updated_on=r[0].updated_on,
    ) for r in rows]


@router.get("/emission-sources/{id}/units", response_model=List[UnitOptionOut])
async def list_units_for_source(
    id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """Return distinct units from all emission factors linked to this source,
    plus any units reachable via unit_conversions from those canonical units."""
    ef = EmissionFactor
    stmt = (
        select(distinct(ef.measurement_unit_id))
        .where(ef.emission_source_id == id)
        .where(ef.is_active == True)
        .where(ef.measurement_unit_id.isnot(None))
    )
    canonical_ids = [r[0] for r in (await db.execute(stmt)).all()]
    return await build_unit_options_with_conversions(db, canonical_ids)


# ------------------------------------------
# Emission Factors (GET) with names resolved
# ------------------------------------------
@router.get("/emission-factors", response_model=List[EmissionFactorOut])
async def list_emission_factors(
    emission_source_id: Optional[UUID] = Query(None),
    measurement_unit_id: Optional[UUID] = Query(None),
    only_active: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    ef = EmissionFactor
    es = EmissionSource
    u = Unit

    stmt = select(
        ef,
        es.name.label("source_name"),
        u.code.label("unit_name")
    ).join(es, ef.emission_source_id == es.id
    ).join(u, ef.measurement_unit_id == u.id)

    if emission_source_id:
        stmt = stmt.where(ef.emission_source_id == emission_source_id)
    if measurement_unit_id:
        stmt = stmt.where(ef.measurement_unit_id == measurement_unit_id)
    if only_active is not None:
        stmt = stmt.where(ef.is_active == only_active)

    stmt = stmt.order_by(es.name, u.code).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).all()

    return [EmissionFactorOut(
        id=r[0].id,
        emission_source_id=r[0].emission_source_id,
        emission_source_name=r[1],
        measurement_unit_id=r[0].measurement_unit_id,
        measurement_unit_name=r[2],
        is_active=r[0].is_active,
        created_on=r[0].created_on,
        updated_on=r[0].updated_on
    ) for r in rows]

# ------------------------------------------------
# Emission Factor Values (GET): per-factor stages
# ------------------------------------------------
@router.get("/emission-factors/{id}/values", response_model=List[EmissionFactorValueOut])
async def list_emission_factor_values(
    id: UUID,
    db: AsyncSession = Depends(get_session),
):
    ev = EmissionFactorValue
    stmt = select(ev).where(ev.emission_factor_id == id).order_by(ev.stage_code)
    rows = (await db.execute(stmt)).scalars().all()
    return [EmissionFactorValueOut(
        id=r.id,
        emission_factor_id=r.emission_factor_id,
        stage_code=r.stage_code,
        gwp_kgco2e_per_unit=r.gwp_kgco2e_per_unit,
        created_on=r.created_on,
        updated_on=r.updated_on
    ) for r in rows]

# ------------------------------------------------------------
# Convenience: factor + its values together (a single payload)
# ------------------------------------------------------------
@router.get("/emission-factors/{id}", response_model=EmissionFactorWithValuesOut)
async def get_emission_factor_with_values(
    id: UUID,
    db: AsyncSession = Depends(get_session),
):
    ef = EmissionFactor
    es = EmissionSource
    u = Unit
    ev = EmissionFactorValue

    # header with names
    stmt_header = select(
        ef,
        es.name.label("source_name"),
        u.code.label("unit_name")
    ).join(es, ef.emission_source_id == es.id
    ).join(u, ef.measurement_unit_id == u.id
    ).where(ef.id == id)

    header = (await db.execute(stmt_header)).first()
    if not header:
        raise HTTPException(status_code=404, detail="Emission factor not found")

    ef_row, source_name, unit_name = header[0], header[1], header[2]
    factor_out = EmissionFactorOut(
        id=ef_row.id,
        emission_source_id=ef_row.emission_source_id,
        emission_source_name=source_name,
        measurement_unit_id=ef_row.measurement_unit_id,
        measurement_unit_name=unit_name,
        is_active=ef_row.is_active,
        created_on=ef_row.created_on,
        updated_on=ef_row.updated_on
    )

    # values
    stmt_values = select(ev).where(ev.emission_factor_id == id).order_by(ev.stage_code)
    values = (await db.execute(stmt_values)).scalars().all()
    values_out = [EmissionFactorValueOut(
        id=r.id,
        emission_factor_id=r.emission_factor_id,
        stage_code=r.stage_code,
        gwp_kgco2e_per_unit=r.gwp_kgco2e_per_unit,
        created_on=r.created_on,
        updated_on=r.updated_on
    ) for r in values]

    return EmissionFactorWithValuesOut(factor=factor_out, values=values_out)
