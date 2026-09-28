from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as sa_select

from core.session import get_session
from crud.audit_logs import write_audit_event
from crud.project import touch_project, get_project
from crud.dataset_revisions import list_dataset_revisions, get_published_dataset_revision
from schemas.dataset_revisions import DatasetRevisionOut
from schemas.project_dataset_revisions import (
    ProjectDatasetRevisionCreate,
    ProjectDatasetRevisionOut,
    ProjectDatasetRevisionMigrationOut,
    ProjectDatasetRevisionUpdate,
)
from crud.project_dataset_revisions import (
    create_project_dataset_revision,
    get_project_dataset_revision,
    get_revision_status,
    list_project_dataset_revisions_by_project,
    update_project_dataset_revision,
    delete_project_dataset_revision,
    upsert_project_dataset_revision,
)
from models.project_dataset_revisions import ProjectDatasetRevision as ProjectDatasetRevisionModel
from services.project_dataset_recalculation import (
    ProjectDatasetRecalculationError,
    recalculate_project_for_revision,
)


router = APIRouter(prefix="/api/project-dataset-revisions", tags=["project-dataset-revisions"])


class MigrateRequest(BaseModel):
    project_id: UUID
    to_revision_id: UUID
    notes: Optional[str] = None


@router.post("", response_model=ProjectDatasetRevisionMigrationOut, status_code=status.HTTP_201_CREATED)
async def create_new_project_dataset_revision(payload: ProjectDatasetRevisionCreate, db: AsyncSession = Depends(get_session)):
    rev_status = await get_revision_status(db, payload.dataset_revision_id)
    if rev_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset revision not found",
        )
    if rev_status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot bind a project to a revision with status '{rev_status}' (must be 'published')",
        )
    obj = await upsert_project_dataset_revision(db, payload)
    try:
        recalc_report = await recalculate_project_for_revision(
            db, obj.project_id, obj.dataset_revision_id
        )
    except ProjectDatasetRecalculationError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The dataset revision was not changed because some entries could not be recalculated.",
                **exc.report,
            },
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The dataset revision was not changed because recalculation failed.",
                "missing_data": [],
                "calculation_errors": [{"entry": "Project recalculation", "message": str(exc)}],
            },
        ) from exc
    obj.calculation_report = recalc_report
    await touch_project(db, obj.project_id)
    await db.commit()
    await write_audit_event(
        db,
        entity_type="project_dataset_revision",
        entity_id=obj.id,
        action="CREATE",
        metadata={"project_id": str(obj.project_id), "revision_id": str(obj.dataset_revision_id)},
    )
    await db.commit()
    result = await db.execute(sa_select(ProjectDatasetRevisionModel).where(ProjectDatasetRevisionModel.id == obj.id))
    output = ProjectDatasetRevisionMigrationOut.model_validate(result.scalars().first() or obj)
    return output.model_copy(update=recalc_report)


@router.post("/migrate", response_model=ProjectDatasetRevisionMigrationOut, status_code=status.HTTP_201_CREATED)
async def migrate_project_revision(
    payload: MigrateRequest,
    db: AsyncSession = Depends(get_session),
):
    rev_status = await get_revision_status(db, payload.to_revision_id)
    if rev_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target dataset revision not found")
    if rev_status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot migrate a project to a revision with status '{rev_status}' (must be 'published')",
        )
    new_pdr = await upsert_project_dataset_revision(
        db,
        ProjectDatasetRevisionCreate(
            project_id=payload.project_id,
            dataset_revision_id=payload.to_revision_id,
            notes=payload.notes,
        ),
    )
    try:
        recalc_report = await recalculate_project_for_revision(
            db, payload.project_id, payload.to_revision_id
        )
    except ProjectDatasetRecalculationError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The dataset revision was not changed because some entries could not be recalculated.",
                **exc.report,
            },
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The dataset revision was not changed because recalculation failed.",
                "missing_data": [],
                "calculation_errors": [{"entry": "Project recalculation", "message": str(exc)}],
            },
        ) from exc
    new_pdr.calculation_report = recalc_report
    await touch_project(db, payload.project_id)
    await db.commit()
    await write_audit_event(
        db,
        entity_type="project_dataset_revision",
        entity_id=new_pdr.id,
        action="MIGRATE",
        metadata={
            "project_id": str(payload.project_id),
            "to_revision_id": str(payload.to_revision_id),
            "recalculated_rows": recalc_report["recalculated_count"],
            "missing_data_count": len(recalc_report["missing_data"]),
            "calculation_error_count": len(recalc_report["calculation_errors"]),
        },
    )
    await db.commit()
    result = await db.execute(sa_select(ProjectDatasetRevisionModel).where(ProjectDatasetRevisionModel.id == new_pdr.id))
    output = ProjectDatasetRevisionMigrationOut.model_validate(result.scalars().first() or new_pdr)
    return output.model_copy(update=recalc_report)


@router.get("/by-project/{project_id}", response_model=List[ProjectDatasetRevisionOut])
async def get_project_dataset_revisions_by_project(project_id: UUID, db: AsyncSession = Depends(get_session)):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = await list_project_dataset_revisions_by_project(db, project_id)
    if existing:
        return existing

    latest_default = await get_published_dataset_revision(db)
    if latest_default is None:
        return []

    auto_bound = await upsert_project_dataset_revision(
        db,
        ProjectDatasetRevisionCreate(
            project_id=project_id,
            dataset_revision_id=latest_default.id,
            notes="Auto-assigned latest published DEFAULT dataset revision",
        ),
    )
    try:
        auto_bound.calculation_report = await recalculate_project_for_revision(
            db, project_id, latest_default.id
        )
    except ProjectDatasetRecalculationError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The default dataset could not be assigned because some entries could not be recalculated.",
                **exc.report,
            },
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "dataset_recalculation_failed",
                "message": "The default dataset was not assigned because recalculation failed.",
                "missing_data": [],
                "calculation_errors": [{"entry": "Project recalculation", "message": str(exc)}],
            },
        ) from exc
    await touch_project(db, project_id)
    await db.commit()
    await write_audit_event(
        db,
        entity_type="project_dataset_revision",
        entity_id=auto_bound.id,
        action="AUTO_ASSIGN_DEFAULT",
        metadata={
            "project_id": str(project_id),
            "revision_id": str(latest_default.id),
        },
    )
    await db.commit()
    result = await db.execute(
        sa_select(ProjectDatasetRevisionModel).where(ProjectDatasetRevisionModel.id == auto_bound.id)
    )
    return [result.scalars().first() or auto_bound]


@router.get("/{pdr_id}", response_model=ProjectDatasetRevisionOut)
async def get_project_dataset_revision_by_id(pdr_id: UUID, db: AsyncSession = Depends(get_session)):
    obj = await get_project_dataset_revision(db, pdr_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset revision not found"
        )
    return obj


@router.patch("/{pdr_id}", response_model=ProjectDatasetRevisionOut)
async def patch_project_dataset_revision(pdr_id: UUID, payload: ProjectDatasetRevisionUpdate, db: AsyncSession = Depends(get_session)):
    obj = await get_project_dataset_revision(db, pdr_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset revision not found"
        )
    obj = await update_project_dataset_revision(db, obj, payload)
    await db.commit()
    return obj


@router.delete("/{pdr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_dataset_revision(pdr_id: UUID, db: AsyncSession = Depends(get_session)):
    ok = await delete_project_dataset_revision(db, pdr_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset revision not found"
        )
    await db.commit()
    return None


@router.get("/bindable/{project_id}", response_model=List[DatasetRevisionOut])
async def get_bindable_dataset_revisions(
    project_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    org_id = project.proponent_org_id

    default_revs = await list_dataset_revisions(db, status="published", scope_type="DEFAULT")
    org_revs = await list_dataset_revisions(db, status="published", scope_type="ORG", scope_id=org_id)
    project_revs = await list_dataset_revisions(db, status="published", scope_type="PROJECT", scope_id=project_id)

    return [*default_revs, *org_revs, *project_revs]
