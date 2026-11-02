
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from pydantic import BaseModel
from core.session import get_session

router = APIRouter(prefix="/api/views", tags=["views"])

# ---- Response model for the view row ----
class EmissionFactorValuesPivotRow(BaseModel):
    emission_factor_id: UUID
    emission_source_id: UUID
    emission_source_name: str
    measurement_unit_id: UUID
    measurement_unit_name: str
    emissions_sub_category_id: Optional[UUID] = None
    emissions_sub_category_name: Optional[str] = None
    emissions_category_id: Optional[UUID] = None
    emissions_category_name: Optional[str] = None
    a1_3: Optional[Decimal] = None
    a4: Optional[Decimal] = None
    a5: Optional[Decimal] = None
    b2_5: Optional[Decimal] = None
    c2: Optional[Decimal] = None
    c3_4: Optional[Decimal] = None

    class Config:
        from_attributes = False  # We're mapping raw query dicts, not ORM objects.

@router.get("/emission-factor-values-pivot", response_model=List[EmissionFactorValuesPivotRow])
async def get_emission_factor_values_pivot(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    emissions_category_id: Optional[UUID] = None,
    emissions_sub_category_id: Optional[UUID] = None,
    emission_source_id: Optional[UUID] = None,
    measurement_unit_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    """
    Read rows from the Postgres view: public.v_emission_factor_values_pivot
    Supports filtering by category, sub-category, source, and unit.
    """

    base_sql = """
        SELECT
            emission_factor_id,
            emission_source_id,
            emission_source_name,
            measurement_unit_id,
            measurement_unit_name,
            emissions_sub_category_id,
            emissions_sub_category_name,
            emissions_category_id,
            emissions_category_name,
            a1_3, a4, a5, b2_5, c2, c3_4
        FROM public.v_emission_factor_values_pivot
        WHERE 1=1
    """

    params = {}
    if emissions_category_id:
        base_sql += " AND emissions_category_id = :emissions_category_id"
        params["emissions_category_id"] = str(emissions_category_id)
    if emissions_sub_category_id:
        base_sql += " AND emissions_sub_category_id = :emissions_sub_category_id"
        params["emissions_sub_category_id"] = str(emissions_sub_category_id)
    if emission_source_id:
        base_sql += " AND emission_source_id = :emission_source_id"
        params["emission_source_id"] = str(emission_source_id)
    if measurement_unit_id:
        base_sql += " AND measurement_unit_id = :measurement_unit_id"
        params["measurement_unit_id"] = str(measurement_unit_id)

    base_sql += " ORDER BY emission_source_name, measurement_unit_name"
    base_sql += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = limit

    result = await db.execute(text(base_sql), params)
    # Convert SQLAlchemy Row objects to dict for Pydantic
    rows = [dict(r._mapping) for r in result.fetchall()]
    return rows