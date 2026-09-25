"""
test_dataset_authorization.py
=============================
Unit tests for core/dataset_authorization.py assert_revision_edit_permission.
"""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.dataset_authorization import assert_revision_edit_permission
from core.rbac import (
    GENERAL_USER,
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    SUPER_ADMIN,
)
from core.security import Principal


class FakeSessionWithRevision:
    def __init__(self, revision=None):
        self._revision = revision

    async def execute(self, stmt):
        rev = self._revision

        class _Result:
            def scalars(self):
                class _Scalars:
                    def first(self):
                        return rev
                return _Scalars()
        return _Result()


@pytest.mark.asyncio
async def test_read_only_dataset_rejected():
    principal = Principal(user_id=uuid4(), email="admin@example.com")
    session = FakeSessionWithRevision()
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=uuid4(),
            dataset_type="audit_logs",
        )
    assert exc_info.value.status_code == 403
    assert "read-only" in exc_info.value.detail


@pytest.mark.asyncio
async def test_revision_not_found():
    principal = Principal(user_id=uuid4(), email="admin@example.com")
    session = FakeSessionWithRevision(revision=None)
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=uuid4(),
            dataset_type="densities",
        )
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_non_draft_revision_rejected():
    principal = Principal(user_id=uuid4(), email="admin@example.com")
    published_rev = SimpleNamespace(
        id=uuid4(),
        status="published",
        scope_type="DEFAULT",
        scope_id=None,
    )
    session = FakeSessionWithRevision(revision=published_rev)
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=published_rev.id,
            dataset_type="densities",
        )
    assert exc_info.value.status_code == 409
    assert "published" in exc_info.value.detail


@pytest.mark.asyncio
async def test_scope_tier_disallowed_for_dataset():
    # Attempting to edit an ORG_ONLY dataset in a PROJECT scope revision
    principal = Principal(user_id=uuid4(), email="editor@example.com")
    project_rev = SimpleNamespace(
        id=uuid4(),
        status="draft",
        scope_type="PROJECT",
        scope_id=uuid4(),
    )
    session = FakeSessionWithRevision(revision=project_rev)
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=project_rev.id,
            dataset_type="carbon_values",  # ORG_ONLY
        )
    assert exc_info.value.status_code == 403
    assert "cannot be modified in a 'PROJECT' revision" in exc_info.value.detail


@pytest.mark.asyncio
async def test_default_revision_requires_super_admin(monkeypatch):
    import core.dataset_authorization as da

    user_id = uuid4()
    principal = Principal(user_id=user_id, email="user@example.com")
    default_rev = SimpleNamespace(
        id=uuid4(),
        status="draft",
        scope_type="DEFAULT",
        scope_id=None,
    )
    session = FakeSessionWithRevision(revision=default_rev)

    # 1. Non-super-admin -> 403
    async def mock_roles(_db, uid, project_id=None):
        return {ORG_ADMIN}
    monkeypatch.setattr(da, "get_effective_role_names", mock_roles)

    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=default_rev.id,
            dataset_type="densities",
        )
    assert exc_info.value.status_code == 403
    assert "Super Admin" in exc_info.value.detail

    # 2. Super Admin -> succeeds
    async def mock_sa_roles(_db, uid, project_id=None):
        return {SUPER_ADMIN}
    monkeypatch.setattr(da, "get_effective_role_names", mock_sa_roles)

    await assert_revision_edit_permission(
        db=session,
        principal=principal,
        dataset_revision_id=default_rev.id,
        dataset_type="densities",
    )


@pytest.mark.asyncio
async def test_org_revision_authorization(monkeypatch):
    import core.dataset_authorization as da

    user_id = uuid4()
    org_id = uuid4()
    principal = Principal(user_id=user_id, email="orgadmin@example.com")
    org_rev = SimpleNamespace(
        id=uuid4(),
        status="draft",
        scope_type="ORG",
        scope_id=org_id,
    )
    session = FakeSessionWithRevision(revision=org_rev)

    # 1. User without ORG_ADMIN or SUPER_ADMIN on org_id -> 403
    async def mock_general_roles(_db, uid, o_id):
        return {GENERAL_USER}
    monkeypatch.setattr(da, "get_org_scoped_role_names", mock_general_roles)

    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=org_rev.id,
            dataset_type="carbon_values",
        )
    assert exc_info.value.status_code == 403
    assert "Organisation Admin" in exc_info.value.detail

    # 2. ORG_ADMIN -> succeeds
    async def mock_org_roles(_db, uid, o_id):
        return {ORG_ADMIN}
    monkeypatch.setattr(da, "get_org_scoped_role_names", mock_org_roles)

    await assert_revision_edit_permission(
        db=session,
        principal=principal,
        dataset_revision_id=org_rev.id,
        dataset_type="carbon_values",
    )


@pytest.mark.asyncio
async def test_project_revision_authorization(monkeypatch):
    import core.dataset_authorization as da

    user_id = uuid4()
    project_id = uuid4()
    principal = Principal(user_id=user_id, email="editor@example.com")
    project_rev = SimpleNamespace(
        id=uuid4(),
        status="draft",
        scope_type="PROJECT",
        scope_id=project_id,
    )
    session = FakeSessionWithRevision(revision=project_rev)

    # 1. PROJECT_VIEWER -> 403
    async def mock_viewer_roles(_db, uid, project_id=None):
        return {PROJECT_VIEWER}
    monkeypatch.setattr(da, "get_effective_role_names", mock_viewer_roles)

    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=project_rev.id,
            dataset_type="default_transport_distances",
        )
    assert exc_info.value.status_code == 403
    assert "Project Admin, Project Editor" in exc_info.value.detail

    # 2. PROJECT_EDITOR -> succeeds
    async def mock_editor_roles(_db, uid, project_id=None):
        return {PROJECT_EDITOR}
    monkeypatch.setattr(da, "get_effective_role_names", mock_editor_roles)

    await assert_revision_edit_permission(
        db=session,
        principal=principal,
        dataset_revision_id=project_rev.id,
        dataset_type="default_transport_distances",
    )
