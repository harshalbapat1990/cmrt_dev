from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core.dataset_authorization import assert_revision_edit_permission
from schemas.background_grade_metrics import (
    BackgroundGradeMetricCreate,
    BackgroundGradeMetricOut,
    BackgroundGradeMetricUpdate,
)
from crud.background_grade_metrics import (
    create_background_grade_metric,
    get_background_grade_metric,
    get_background_grade_metric_orm,
    list_background_grade_metrics,
    supersede_background_grade_metric,
    delete_background_grade_metric,
)

from core.dataset_authorization import protect_dataset_reads

router = APIRouter(prefix="/api/background-grade-metrics", tags=["background-grade-metrics"])


@router.post("", response_model=BackgroundGradeMetricOut, status_code=status.HTTP_201_CREATED)
async def create_new_background_grade_metric(
    payload: BackgroundGradeMetricCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="background_grade_metrics",
    )
    obj = await create_background_grade_metric(db, payload)
    await db.commit()
    row = await get_background_grade_metric(db, obj.id)
    return BackgroundGradeMetricOut.model_validate(row)


@router.get("", response_model=List[BackgroundGradeMetricOut])
async def get_background_grade_metrics(
    dataset_revision_id: Optional[UUID] = Query(None),
    dataset_revision_ids: List[UUID] = Query(default=[], description="Filter by multiple dataset revision IDs (multi-value)"),
    grade_id: Optional[int] = Query(None),
    jurisdiction_name: Optional[str] = Query(None, description="Filter by single jurisdiction name (deprecated, use jurisdiction_names)"),
    jurisdiction_names: List[str] = Query(default=[], description="Filter by jurisdiction names (multi-value)"),
    mastertype_id: Optional[UUID] = Query(None, description="Filter by mastertype ID"),
    typecast_id: Optional[UUID] = Query(None, description="Filter by typecast ID"),
    band_code: Optional[str] = Query(None, description="Filter by sensitivity band code (e.g. Mid, High)"),
    emissions_category_id: Optional[UUID] = Query(None, description="Filter by emissions category UUID"),
    emissions_subcategory_id: Optional[UUID] = Query(None, description="Filter by emissions subcategory UUID"),
    emissions_category: List[str] = Query(default=[], description="Filter by emissions category name"),
    emissions_subcategory: List[str] = Query(default=[], description="Filter by emissions sub-category name"),
    emissions_source: Optional[str] = Query(None, description="Text search for emissions source"),
    lifecycle_module_code: Optional[str] = Query(None),
    unit_codes: List[str] = Query(default=[], description="Filter by unit code"),
    metric_type_codes: List[str] = Query(default=[], description="Filter by metric type code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=20000),
    db: AsyncSession = Depends(get_session),
):
    rows = await list_background_grade_metrics(
        db,
        dataset_revision_id=dataset_revision_id,
        dataset_revision_ids=dataset_revision_ids,
        grade_id=grade_id,
        jurisdiction_name=jurisdiction_name,
        jurisdiction_names=jurisdiction_names,
        mastertype_id=mastertype_id,
        typecast_id=typecast_id,
        band_code=band_code,
        emissions_category_id=emissions_category_id,
        emissions_subcategory_id=emissions_subcategory_id,
        emissions_categories=emissions_category,
        emissions_subcategories=emissions_subcategory,
        emissions_source=emissions_source,
        lifecycle_module_code=lifecycle_module_code,
        unit_codes=unit_codes,
        metric_type_codes=metric_type_codes,
        skip=skip,
        limit=limit,
    )
    return [BackgroundGradeMetricOut.model_validate(r) for r in rows]


@router.get("/{metric_id}", response_model=BackgroundGradeMetricOut)
async def get_background_grade_metric_by_id(metric_id: UUID, db: AsyncSession = Depends(get_session)):
    row = await get_background_grade_metric(db, metric_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background grade metric not found")
    return BackgroundGradeMetricOut.model_validate(row)


@router.patch("/{metric_id}", response_model=BackgroundGradeMetricOut)
async def patch_background_grade_metric(
    metric_id: UUID,
    payload: BackgroundGradeMetricUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_background_grade_metric_orm(db, metric_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background grade metric not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="background_grade_metrics",
    )
    new_obj = await supersede_background_grade_metric(db, obj, payload.model_dump(exclude_unset=True))
    await db.commit()
    row = await get_background_grade_metric(db, new_obj.id)
    return BackgroundGradeMetricOut.model_validate(row)


@router.delete("/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_background_grade_metric(
    metric_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_background_grade_metric_orm(db, metric_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background grade metric not found")
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="background_grade_metrics",
    )
    ok = await delete_background_grade_metric(db, obj.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background grade metric not found")
    await db.commit()
    return None

protect_dataset_reads(router)
