from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.session import get_session
from core.security import get_current_principal, Principal
from core import rbac
from core.dataset_authorization import assert_revision_view_permission
from schemas.dataset_revisions import DatasetRevisionBranch, DatasetRevisionCreate, DatasetRevisionOut, DatasetRevisionUpdate
from crud.dataset_revisions import (
    branch_dataset_revision,
    count_bound_projects,
    create_dataset_revision,
    get_dataset_revision,
    get_dataset_revision_by_name,
    list_dataset_revisions,
    set_revision_status,
    update_dataset_revision,
    delete_dataset_revision,
)
from crud.emissions_factor_sets import count_factor_sets_for_revision as count_factor_sets
from crud.audit_logs import write_audit_event

router = APIRouter(prefix="/api/dataset-revisions", tags=["dataset-revisions"])

# Status transitions validation rules:
# draft      → published  (via /publish)  — no restrictions
# published  → draft      (via /unpublish) — requires no bound projects
# published  → deprecated (via /deprecate) — no restrictions; represents supersession
# published  → archived   (via /archive)  — requires no bound projects
# deprecated → archived   (via /archive)  — requires no bound projects
# draft      → archived   (via /archive)  — requires no bound projects
# archived   → (terminal) — no outgoing transitions allowed


async def _assert_revision_permission(
    db: AsyncSession,
    principal: Principal,
    scope_type: str,
    scope_id,
    is_archive: bool = False,
) -> None:
    uid = principal.user_id
    if scope_type == "DEFAULT":
        roles = await rbac.get_effective_role_names(db, uid)
        if rbac.SUPER_ADMIN not in roles:
            raise HTTPException(status_code=403, detail="Only Super Admin may modify default revisions")
    elif scope_type == "ORG":
        if scope_id is None:
            raise HTTPException(status_code=400, detail="ORG revisions require a scope_id (org UUID)")
        roles = await rbac.get_org_scoped_role_names(db, uid, scope_id)
        if is_archive:
            if rbac.ORG_ADMIN not in roles:
                raise HTTPException(status_code=403, detail="Only the owning Org Admin may archive org revisions")
        else:
            if rbac.ORG_ADMIN not in roles:
                raise HTTPException(status_code=403, detail="Only Org Admin may modify org revisions")
    elif scope_type == "PROJECT":
        if scope_id is None:
            raise HTTPException(status_code=400, detail="PROJECT revisions require a scope_id (project UUID)")
        roles = await rbac.get_effective_role_names(db, uid, project_id=scope_id)
        allowed = {rbac.PROJECT_ADMIN, rbac.PROJECT_EDITOR}
        if not set(roles) & allowed:
            raise HTTPException(status_code=403, detail="Only Project Admin or Project Editor may modify project revisions")


@router.post("", response_model=DatasetRevisionOut, status_code=status.HTTP_201_CREATED)
async def create_new_dataset_revision(
    payload: DatasetRevisionCreate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    if payload.scope_type == "DEFAULT" and payload.scope_id is not None:
        raise HTTPException(status_code=422, detail="DEFAULT revisions must not have a scope_id")
    if payload.scope_type != "DEFAULT" and payload.scope_id is None:
        raise HTTPException(status_code=422, detail=f"{payload.scope_type} revisions require a scope_id")
    if payload.scope_type != "DEFAULT":
        raise HTTPException(status_code=422, detail="Org and project revisions must be created by branching a published source revision")
    await _assert_revision_permission(db, principal, payload.scope_type, payload.scope_id)
    payload = payload.model_copy(update={"created_by": principal.user_id})
    existing = await get_dataset_revision_by_name(
        db, payload.name, scope_type=payload.scope_type, scope_id=payload.scope_id
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dataset revision name already exists")
    obj = await create_dataset_revision(db, payload)
    await write_audit_event(db, entity_type="dataset_revision", entity_id=obj.id, action="CREATE")
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{revision_id}/branch", response_model=DatasetRevisionOut, status_code=status.HTTP_201_CREATED)
async def branch_dataset_revision_endpoint(
    revision_id: UUID,
    payload: DatasetRevisionBranch,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    if payload.scope_type == "DEFAULT" and payload.scope_id is not None:
        raise HTTPException(status_code=422, detail="DEFAULT revisions must not have a scope_id")
    if payload.scope_type != "DEFAULT" and payload.scope_id is None:
        raise HTTPException(status_code=422, detail=f"{payload.scope_type} revisions require a scope_id")
    await _assert_revision_permission(db, principal, payload.scope_type, payload.scope_id)
    source = await get_dataset_revision(db, revision_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source revision not found")
    if source.status != "published":
        raise HTTPException(status_code=409, detail="Only published revisions can be used as a branch source")
    source_scope = (source.scope_type or "DEFAULT").upper()
    destination_scope = payload.scope_type.upper()
    allowed_sources = {
        "DEFAULT": {"DEFAULT"},
        "ORG": {"DEFAULT", "ORG"},
        "PROJECT": {"DEFAULT", "ORG", "PROJECT"},
    }
    if source_scope not in allowed_sources.get(destination_scope, set()):
        raise HTTPException(status_code=403, detail="Source revision scope is not allowed for this branch")
    if source_scope == "ORG" and destination_scope in {"ORG", "PROJECT"}:
        from models.project import Project
        if destination_scope == "ORG" and source.scope_id != payload.scope_id:
            raise HTTPException(status_code=403, detail="Org branches may only use a global or same-org source")
        if destination_scope == "PROJECT":
            result = await db.execute(select(Project.proponent_org_id).where(Project.id == payload.scope_id))
            if result.scalar_one_or_none() != source.scope_id:
                raise HTTPException(status_code=403, detail="Project branches may only use their owning organisation's source")
    if source_scope == "PROJECT" and (destination_scope != "PROJECT" or source.scope_id != payload.scope_id):
        raise HTTPException(status_code=403, detail="Project branches may only use a source from the same project")
    existing = await get_dataset_revision_by_name(
        db, payload.name, scope_type=payload.scope_type, scope_id=payload.scope_id
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dataset revision name already exists")
    new_rev = await branch_dataset_revision(
        db, revision_id, payload.name, payload.notes,
        scope_type=payload.scope_type, scope_id=payload.scope_id,
    )
    await write_audit_event(
        db, entity_type="dataset_revision", entity_id=new_rev.id,
        action="BRANCH", metadata={"source_id": str(revision_id)},
    )
    await db.commit()
    await db.refresh(new_rev)
    return new_rev


@router.get("", response_model=List[DatasetRevisionOut])
async def get_dataset_revisions(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by lifecycle status: draft | published | deprecated | archived",
    ),
    scope_type: Optional[str] = Query(
        None,
        description="Filter by scope tier: DEFAULT | ORG | PROJECT",
    ),
    scope_id: Optional[UUID] = Query(
        None,
        description="Filter by scope owner UUID (org_id or project_id)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    # Visibility must be applied before caller filters and pagination, otherwise
    # a caller could infer or request revisions outside their scope.
    candidates = await list_dataset_revisions(db, skip=0, limit=10000)
    visible = []
    for revision in candidates:
        try:
            await assert_revision_view_permission(db, principal, revision)
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        if status_filter and revision.status != status_filter:
            continue
        if scope_type and revision.scope_type != scope_type:
            continue
        if scope_id is not None and revision.scope_id != scope_id:
            continue
        visible.append(revision)
    return visible[skip:skip + limit]


@router.get("/{revision_id}", response_model=DatasetRevisionOut)
async def get_dataset_revision_by_id(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await assert_revision_view_permission(db, principal, obj)
    return obj


@router.patch("/{revision_id}", response_model=DatasetRevisionOut)
async def patch_dataset_revision(
    revision_id: UUID,
    payload: DatasetRevisionUpdate,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id)
    if obj.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived revisions cannot be edited",
        )
    obj = await update_dataset_revision(db, obj, payload)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{revision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dataset_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id)
    bound = await count_bound_projects(db, revision_id)
    if bound:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {bound} project(s) are bound to this revision",
        )
    factor_set_count = await count_factor_sets(db, revision_id)
    if factor_set_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {factor_set_count} emissions factor set(s) belong to this revision",
        )
    await write_audit_event(db, entity_type="dataset_revision", entity_id=revision_id, action="DELETE")
    await delete_dataset_revision(db, revision_id)
    await db.commit()
    return None


@router.post("/{revision_id}/publish", response_model=DatasetRevisionOut)
async def publish_dataset_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id)
    if obj.status not in ("draft",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot publish a revision with status '{obj.status}' (must be 'draft')",
        )
    factor_set_count = await count_factor_sets(db, revision_id)
    if factor_set_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot publish a dataset revision without at least one emissions factor set",
        )
    obj = await set_revision_status(db, obj, "published")
    await write_audit_event(
        db, entity_type="dataset_revision", entity_id=obj.id,
        action="PUBLISH", new_value="published",
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{revision_id}/unpublish", response_model=DatasetRevisionOut)
async def unpublish_dataset_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id)
    if obj.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot unpublish a revision with status '{obj.status}' (must be 'published')",
        )
    bound = await count_bound_projects(db, revision_id)
    if bound:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot unpublish: {bound} project(s) are bound to this revision. Create a new revision instead.",
        )
    obj = await set_revision_status(db, obj, "draft")
    await write_audit_event(
        db, entity_type="dataset_revision", entity_id=obj.id,
        action="UNPUBLISH", new_value="draft",
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{revision_id}/deprecate", response_model=DatasetRevisionOut)
async def deprecate_dataset_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id)
    if obj.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot deprecate a revision with status '{obj.status}' (must be 'published')",
        )
    obj = await set_revision_status(db, obj, "deprecated")
    await write_audit_event(
        db, entity_type="dataset_revision", entity_id=obj.id,
        action="DEPRECATE", new_value="deprecated",
    )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{revision_id}/archive", response_model=DatasetRevisionOut)
async def archive_dataset_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
):
    obj = await get_dataset_revision(db, revision_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset revision not found")
    await _assert_revision_permission(db, principal, obj.scope_type, obj.scope_id, is_archive=True)
    if obj.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revision is already archived",
        )
    bound = await count_bound_projects(db, revision_id)
    if bound:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot archive: {bound} project(s) are bound to this revision. Create a new revision instead.",
        )
    obj = await set_revision_status(db, obj, "archived")
    await write_audit_event(
        db, entity_type="dataset_revision", entity_id=obj.id,
        action="ARCHIVE", new_value="archived",
    )
    await db.commit()
    await db.refresh(obj)
    return obj
