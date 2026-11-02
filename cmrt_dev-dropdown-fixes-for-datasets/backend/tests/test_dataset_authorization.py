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

from core.dataset_authorization import (
    assert_revision_edit_permission,
    require_dataset_read_access,
    assert_dataset_revision_read_permission,
)
from core.rbac import (
    GENERAL_USER,
    ORG_ADMIN,
    PROJECT_ADMIN,
    PROJECT_EDITOR,
    PROJECT_VIEWER,
    SUPER_ADMIN,
)
from core.security import Principal
from starlette.requests import Request


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
async def test_unregistered_dataset_type_rejected():
    principal = Principal(user_id=uuid4(), email="admin@example.com")
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=FakeSessionWithRevision(),
            principal=principal,
            dataset_type="new_unregistered_dataset",
        )
    assert exc_info.value.status_code == 403
    assert "no registered governance category" in exc_info.value.detail


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
    await assert_revision_edit_permission(
        db=session,
        principal=principal,
        dataset_revision_id=default_rev.id,
        dataset_type="direct_substitutions",
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
    await assert_revision_edit_permission(
        db=session,
        principal=principal,
        dataset_revision_id=org_rev.id,
        dataset_type="direct_substitutions",
    )

    async def mock_superadmin_roles(_db, uid, o_id):
        return {SUPER_ADMIN}
    monkeypatch.setattr(da, "get_org_scoped_role_names", mock_superadmin_roles)
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=org_rev.id,
            dataset_type="carbon_values",
        )
    assert exc_info.value.status_code == 403


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

    async def mock_superadmin_roles(_db, uid, project_id=None):
        return {SUPER_ADMIN}
    monkeypatch.setattr(da, "get_effective_role_names", mock_superadmin_roles)
    with pytest.raises(HTTPException) as exc_info:
        await assert_revision_edit_permission(
            db=session,
            principal=principal,
            dataset_revision_id=project_rev.id,
            dataset_type="default_transport_distances",
        )
    assert exc_info.value.status_code == 403


def _read_request(path: str, query: str = "", endpoint_name: str = "lookup") -> Request:
    async def endpoint():
        return None

    endpoint.__name__ = endpoint_name
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
        "path_params": {},
        "route": SimpleNamespace(endpoint=endpoint),
    })


@pytest.mark.asyncio
async def test_revision_read_check_authorizes_selected_revision(monkeypatch):
    import core.dataset_authorization as da

    revision_id = uuid4()
    revision = SimpleNamespace(
        id=revision_id,
        status="published",
        scope_type="DEFAULT",
        scope_id=None,
    )
    authorized = []

    async def get_revision(_db, requested_id):
        assert requested_id == revision_id
        return revision

    async def check_visibility(_db, _principal, requested_revision):
        authorized.append(requested_revision.id)

    monkeypatch.setattr(da, "get_dataset_revision", get_revision)
    monkeypatch.setattr(da, "assert_revision_view_permission", check_visibility)

    await require_dataset_read_access(
        _read_request("/lookup/bgm-categories", f"dataset_revision_id={revision_id}"),
        FakeSessionWithRevision(),
        Principal(user_id=uuid4(), email="reader@example.com"),
    )
    assert authorized == [revision_id]


@pytest.mark.asyncio
async def test_revision_read_check_resolves_project_binding(monkeypatch):
    import core.dataset_authorization as da
    import crud.project_dataset_revisions as project_revision_crud

    project_id, revision_id = uuid4(), uuid4()
    revision = SimpleNamespace(
        id=revision_id,
        status="published",
        scope_type="PROJECT",
        scope_id=project_id,
    )
    authorized = []

    async def list_bindings(_db, requested_project_id):
        assert requested_project_id == project_id
        return [SimpleNamespace(dataset_revision_id=revision_id)]

    async def get_revision(_db, requested_id):
        assert requested_id == revision_id
        return revision

    async def check_visibility(_db, _principal, requested_revision):
        authorized.append(requested_revision.id)

    monkeypatch.setattr(project_revision_crud, "list_project_dataset_revisions_by_project", list_bindings)
    monkeypatch.setattr(da, "get_dataset_revision", get_revision)
    monkeypatch.setattr(da, "assert_revision_view_permission", check_visibility)

    await require_dataset_read_access(
        _read_request("/lookup/bgm-categories", f"project_id={project_id}"),
        FakeSessionWithRevision(),
        Principal(user_id=uuid4(), email="reader@example.com"),
    )
    assert authorized == [revision_id]


@pytest.mark.asyncio
async def test_revision_read_check_requires_selector_without_project_binding():
    with pytest.raises(HTTPException) as exc_info:
        await require_dataset_read_access(
            _read_request("/lookup/bgm-source-units"),
            FakeSessionWithRevision(),
            Principal(user_id=uuid4(), email="reader@example.com"),
        )
    assert exc_info.value.status_code == 400
    assert "dataset_revision_id is required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_project_calculation_uses_and_authorizes_bound_revision(monkeypatch):
    import core.dataset_authorization as da
    import crud.project_dataset_revisions as project_revision_crud

    project_id, bound_revision_id = uuid4(), uuid4()
    calls = []

    async def require_project_access(_db, _principal, requested_project_id, _minimum_access):
        assert requested_project_id == project_id

    async def list_bindings(_db, requested_project_id):
        assert requested_project_id == project_id
        return [SimpleNamespace(dataset_revision_id=bound_revision_id)]

    async def revision_view(_db, _principal, revision_id):
        calls.append(revision_id)

    monkeypatch.setattr(da.rbac, "require_project_access", require_project_access)
    monkeypatch.setattr(project_revision_crud, "list_project_dataset_revisions_by_project", list_bindings)
    monkeypatch.setattr(da, "assert_dataset_revision_read_permission", revision_view)
    principal = Principal(user_id=uuid4(), email="project@example.com")

    resolved = await da.assert_project_dataset_revision_read_permission(
        FakeSessionWithRevision(), principal, project_id
    )
    assert resolved == bound_revision_id
    assert calls == [bound_revision_id]

    with pytest.raises(HTTPException) as exc_info:
        await da.assert_project_dataset_revision_read_permission(
            FakeSessionWithRevision(), principal, project_id, uuid4()
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_calculation_revision_read_check_hides_unrelated_revision(monkeypatch):
    import core.dataset_authorization as da

    revision_id = uuid4()
    revision = SimpleNamespace(id=revision_id, status="published", scope_type="ORG", scope_id=uuid4())

    async def get_revision(_db, _revision_id):
        return revision

    async def deny_visibility(_db, _principal, _revision):
        raise HTTPException(status_code=404, detail="Dataset revision not found")

    monkeypatch.setattr(da, "get_dataset_revision", get_revision)
    monkeypatch.setattr(da, "assert_revision_view_permission", deny_visibility)

    with pytest.raises(HTTPException) as exc_info:
        await assert_dataset_revision_read_permission(
            FakeSessionWithRevision(),
            Principal(user_id=uuid4(), email="reader@example.com"),
            revision_id,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_draft_visibility_is_limited_to_scope_editors(monkeypatch):
    import core.dataset_authorization as da

    user_id, org_id, project_id = uuid4(), uuid4(), uuid4()
    principal = Principal(user_id=user_id, email="editor@example.com")

    async def org_roles(_db, _user_id, requested_org_id):
        return {ORG_ADMIN} if requested_org_id == org_id else {GENERAL_USER}

    async def project_roles(_db, _user_id, project_id=None):
        return {PROJECT_EDITOR} if project_id == project_id_expected else {PROJECT_VIEWER}

    project_id_expected = project_id
    monkeypatch.setattr(da, "get_org_scoped_role_names", org_roles)
    monkeypatch.setattr(da, "get_effective_role_names", project_roles)

    await da.assert_revision_view_permission(
        FakeSessionWithRevision(),
        principal,
        SimpleNamespace(id=uuid4(), status="draft", scope_type="ORG", scope_id=org_id),
    )
    await da.assert_revision_view_permission(
        FakeSessionWithRevision(),
        principal,
        SimpleNamespace(id=uuid4(), status="draft", scope_type="PROJECT", scope_id=project_id),
    )
    with pytest.raises(HTTPException) as exc_info:
        await da.assert_revision_view_permission(
            FakeSessionWithRevision(),
            principal,
            SimpleNamespace(id=uuid4(), status="draft", scope_type="ORG", scope_id=uuid4()),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_published_global_revision_is_visible_to_signed_in_readers():
    import core.dataset_authorization as da

    await da.assert_revision_view_permission(
        FakeSessionWithRevision(),
        Principal(user_id=uuid4(), email="reader@example.com"),
        SimpleNamespace(id=uuid4(), status="published", scope_type="DEFAULT", scope_id=None),
    )


@pytest.mark.asyncio
async def test_published_revision_visibility_follows_scope_membership(monkeypatch):
    import core.dataset_authorization as da

    user_id, org_id, project_id = uuid4(), uuid4(), uuid4()
    principal = Principal(user_id=user_id, email="member@example.com", organization_id=org_id)

    class MembershipSession:
        async def execute(self, _stmt):
            class Result:
                def scalars(self):
                    class Scalars:
                        def first(self):
                            return project_id
                    return Scalars()
            return Result()

    expected_project_id = project_id
    async def project_roles(_db, _user_id, project_id=None):
        return {PROJECT_VIEWER} if project_id == expected_project_id else set()

    monkeypatch.setattr(da, "get_effective_role_names", project_roles)
    db = MembershipSession()
    # Owning organisation and a project the reader belongs to are visible.
    await da.assert_revision_view_permission(
        db, principal, SimpleNamespace(id=uuid4(), status="published", scope_type="ORG", scope_id=org_id)
    )
    await da.assert_revision_view_permission(
        db, principal, SimpleNamespace(id=uuid4(), status="published", scope_type="PROJECT", scope_id=project_id)
    )
    # A different organisation is visible only through a project membership in it.
    await da.assert_revision_view_permission(
        db, principal, SimpleNamespace(id=uuid4(), status="published", scope_type="ORG", scope_id=uuid4())
    )


@pytest.mark.asyncio
async def test_category_edit_matrix_matches_scope_policy(monkeypatch):
    import core.dataset_authorization as da

    principal = Principal(user_id=uuid4(), email="editor@example.com")
    revisions = {}

    async def get_revision(_db, revision_id):
        return revisions[revision_id]

    async def global_roles(_db, _user_id, project_id=None):
        return {SUPER_ADMIN}

    async def org_roles(_db, _user_id, _org_id):
        return {ORG_ADMIN}

    async def project_roles(_db, _user_id, project_id=None):
        return {PROJECT_EDITOR}

    async def scoped_org_roles(_db, _user_id, _org_id):
        return {ORG_ADMIN}

    monkeypatch.setattr(da, "get_dataset_revision", get_revision)
    monkeypatch.setattr(da, "get_effective_role_names", global_roles)
    monkeypatch.setattr(da, "get_org_scoped_role_names", scoped_org_roles)

    cases = [
        ("DEFAULT", None, "fugitives", True),
        ("ORG", uuid4(), "fugitives", True),
        ("PROJECT", uuid4(), "fugitives", True),
        ("DEFAULT", None, "carbon_values", True),
        ("ORG", uuid4(), "carbon_values", True),
        ("PROJECT", uuid4(), "carbon_values", False),
        ("DEFAULT", None, "densities", True),
        ("ORG", uuid4(), "densities", False),
        ("PROJECT", uuid4(), "densities", False),
    ]
    db = FakeSessionWithRevision()
    for scope_type, scope_id, dataset_type, allowed in cases:
        revision_id = uuid4()
        revisions[revision_id] = SimpleNamespace(
            id=revision_id, status="draft", scope_type=scope_type, scope_id=scope_id
        )
        monkeypatch.setattr(da, "get_effective_role_names", global_roles)
        if scope_type == "PROJECT":
            monkeypatch.setattr(da, "get_effective_role_names", project_roles)
        if allowed:
            await da.assert_revision_edit_permission(db, principal, revision_id, dataset_type)
        else:
            with pytest.raises(HTTPException) as exc_info:
                await da.assert_revision_edit_permission(db, principal, revision_id, dataset_type)
            assert exc_info.value.status_code == 403


def test_revision_aware_lookup_routes_use_read_authorization():
    from core.dataset_authorization import require_dataset_read_access as guard
    from routers.lookup_data import router
    from routers.maintenance_replacement_factors import router as maintenance_router
    from routers.operational_equipment import router as operational_equipment_router

    protected_paths = {
        "/api/lookup/electricity-units",
        "/api/lookup/benchmark-typecasts/{id}/units",
        "/api/lookup/bgm-categories",
        "/api/lookup/bgm-subcategories",
        "/api/lookup/bgm-sources",
        "/api/lookup/bgm-source-units",
        "/api/lookup/emission-sources/{id}/units",
        "/api/maintenance-replacement-factors/active",
        "/api/operational-equipment",
    }
    all_routes = [*router.routes, *maintenance_router.routes, *operational_equipment_router.routes]
    routes_by_path = {route.path.rstrip("/"): route for route in all_routes}
    normalized_protected_paths = {path.rstrip("/") for path in protected_paths}
    missing_paths = normalized_protected_paths - routes_by_path.keys()
    assert not missing_paths, f"Expected revision-aware lookup routes were not registered: {sorted(missing_paths)}"

    def dependency_calls(dependant):
        calls = {dependency.call for dependency in dependant.dependencies}
        for dependency in dependant.dependencies:
            calls.update(dependency_calls(dependency))
        return calls

    for path in protected_paths:
        route = routes_by_path[path.rstrip("/")]
        calls = dependency_calls(route.dependant)
        # Router-level dependencies may be stored separately from the built
        # dependant tree when added after the endpoint was registered.
        calls.update(
            getattr(dependency, "dependency", None)
            for dependency in getattr(route, "dependencies", ())
        )
        assert guard in calls, f"{path} is missing the dataset revision read guard"


def test_dataset_backed_calculations_require_an_authenticated_principal():
    from core.security import get_current_principal
    from routers.concrete_mix_register_calculations import router as concrete_router
    from routers.detailed_level_calcs_operational_elec import router as operational_electricity_router
    from routers.grade1_calculations import router as grade1_router
    from routers.grade2_b4_replacement_calculations import router as grade2_b4_router
    from routers.grade2_calculations import router as grade2_router
    from routers.grade34_detailed_level_construction_calcs import router as grade34_router

    for router in (
        concrete_router,
        operational_electricity_router,
        grade1_router,
        grade2_router,
        grade2_b4_router,
        grade34_router,
    ):
        for route in router.routes:
            if route.path.endswith("/calculate") or "calculate-epd" in route.path or "calculate-simplified" in route.path:
                assert any(dep.call is get_current_principal for dep in route.dependant.dependencies)


def test_benchmark_dimension_lookup_routes_require_authentication():
    from core.security import get_current_principal
    from routers.benchmark_mastertypes import router as mastertypes_router
    from routers.benchmark_typecasts import router as typecasts_router

    for router in (mastertypes_router, typecasts_router):
        for route in router.routes:
            assert any(dep.call is get_current_principal for dep in route.dependant.dependencies)


def test_project_benchmark_lookup_routes_accept_revision_context():
    from routers.benchmark_mastertypes import router as mastertypes_router
    from routers.benchmark_typecasts import router as typecasts_router

    for router, path in (
        (mastertypes_router, "/api/benchmark-mastertypes"),
        (typecasts_router, "/api/benchmark-typecasts"),
    ):
        listing = next(route for route in router.routes if route.path == path)
        parameter_names = {parameter.name for parameter in listing.dependant.query_params}
        assert "project_id" in parameter_names
        assert "dataset_revision_id" in parameter_names


def test_operational_electricity_calculation_requires_revision_id():
    from pydantic import ValidationError
    from services.detailed_level_calcs_operational_elec import OperationalElecRequest

    with pytest.raises(ValidationError, match="dataset_revision_id"):
        OperationalElecRequest.model_validate({
            "jurisdiction": "Australia",
            "region": "National",
            "emission_source": "Grid Electricity",
            "year": 2026,
            "quantity_mwh": 1,
        })
