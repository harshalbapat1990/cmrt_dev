from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.dataset_authorization import assert_revision_edit_permission
from core.security import Principal, get_current_principal
from core.session import get_session
from crud.densities import (
    create_density,
    delete_density,
    get_density,
    get_density_by_key,
    list_densities,
    update_density,
)
from schemas.densities import DensityCreate, DensityOut, DensityUpdate


router = APIRouter(
    prefix="/api/densities",
    tags=["densities"],
)


@router.post(
    "",
    response_model=DensityOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_density(
    payload: DensityCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> DensityOut:
    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=payload.dataset_revision_id,
        dataset_type="densities",
    )

    existing = await get_density_by_key(
        db=db,
        jurisdiction_id=payload.jurisdiction_id,
        dataset=payload.dataset,
        record_key=payload.record_key,
        unit_id=payload.unit_id,
        dataset_revision_id=payload.dataset_revision_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Density entry for this "
                "(jurisdiction, dataset, record_key, unit) "
                "already exists"
            ),
        )

    obj = await create_density(db, payload)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Density entry already exists",
        ) from exc

    await db.refresh(obj)

    return obj


@router.get(
    "",
    response_model=list[DensityOut],
)
async def get_densities(
    dataset: str | None = None,
    jurisdiction_id: UUID | None = None,
    unit_id: UUID | None = None,
    search: str | None = None,
    dataset_revision_id: UUID | None = Query(
        default=None,
        description="Filter by dataset revision",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
):
    return await list_densities(
        db=db,
        dataset=dataset,
        jurisdiction_id=jurisdiction_id,
        unit_id=unit_id,
        search=search,
        dataset_revision_id=dataset_revision_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{density_id}",
    response_model=DensityOut,
)
async def get_density_by_id(
    density_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    obj = await get_density(
        db=db,
        density_id=density_id,
    )

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Density not found",
        )

    return obj


@router.patch(
    "/{density_id}",
    response_model=DensityOut,
)
async def patch_density(
    density_id: UUID,
    payload: DensityUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_density(
        db=db,
        density_id=density_id,
    )

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Density not found",
        )

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="densities",
    )

    changes = payload.model_dump(exclude_unset=True)

    unique_fields = {
        "record_key",
        "unit_id",
        "dataset",
        "jurisdiction_id",
    }

    if unique_fields.intersection(changes):
        existing = await get_density_by_key(
            db=db,
            jurisdiction_id=(
                changes["jurisdiction_id"]
                if "jurisdiction_id" in changes
                else obj.jurisdiction_id
            ),
            dataset=(
                changes["dataset"]
                if "dataset" in changes
                else obj.dataset
            ),
            record_key=(
                changes["record_key"]
                if "record_key" in changes
                else obj.record_key
            ),
            unit_id=(
                changes["unit_id"]
                if "unit_id" in changes
                else obj.unit_id
            ),
            dataset_revision_id=obj.dataset_revision_id,
        )

        if existing is not None and existing.id != density_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Density entry for this "
                    "(jurisdiction, dataset, record_key, unit) "
                    "already exists"
                ),
            )

    obj = await update_density(
        db=db,
        obj=obj,
        payload=payload,
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Density entry already exists",
        ) from exc

    await db.refresh(obj)

    return obj


@router.delete(
    "/{density_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_density(
    density_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_density(
        db=db,
        density_id=density_id,
    )

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Density not found",
        )

    await assert_revision_edit_permission(
        db=db,
        principal=principal,
        dataset_revision_id=obj.dataset_revision_id,
        dataset_type="densities",
    )

    deleted = await delete_density(
        db=db,
        density_id=density_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Density not found",
        )

    await db.commit()
