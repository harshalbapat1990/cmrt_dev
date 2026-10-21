"""Tests for /api/dataset-revisions endpoints."""
from __future__ import annotations

from uuid import UUID, uuid4
from types import SimpleNamespace

import pytest

_PAYLOAD = {"name": "Austroads Benchmarks v1.0 (2026)"}


async def _create_revision(client, name: str):
    response = await client.post("/api/dataset-revisions", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_list_dataset_revisions_empty(client):
    resp = await client.get("/api/dataset-revisions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_dataset_revision(client):
    resp = await client.post("/api/dataset-revisions", json=_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == _PAYLOAD["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_dataset_revision_conflict(client):
    await client.post("/api/dataset-revisions", json=_PAYLOAD)
    resp = await client.post("/api/dataset-revisions", json=_PAYLOAD)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_dataset_revision_by_id(client):
    create_resp = await client.post("/api/dataset-revisions", json=_PAYLOAD)
    rid = create_resp.json()["id"]
    resp = await client.get(f"/api/dataset-revisions/{rid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rid


@pytest.mark.asyncio
async def test_get_dataset_revision_not_found(client):
    resp = await client.get(f"/api/dataset-revisions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_dataset_revision(client):
    create_resp = await client.post("/api/dataset-revisions", json=_PAYLOAD)
    rid = create_resp.json()["id"]
    resp = await client.patch(f"/api/dataset-revisions/{rid}", json={"notes": "Updated notes"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_patch_dataset_revision_not_found(client):
    resp = await client.patch(f"/api/dataset-revisions/{uuid4()}", json={"notes": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_dataset_revision(client):
    create_resp = await client.post("/api/dataset-revisions", json=_PAYLOAD)
    rid = create_resp.json()["id"]
    assert (await client.delete(f"/api/dataset-revisions/{rid}")).status_code == 204
    assert (await client.get(f"/api/dataset-revisions/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_dataset_revision_not_found(client):
    resp = await client.delete(f"/api/dataset-revisions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_org_revision_must_be_branched_from_published_source(client, dataset_revision_store):
    source_id = await _create_revision(client, "Global source")
    source = dataset_revision_store[UUID(source_id)]
    source.status = "published"
    org_id = uuid4()
    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Org branch", "scope_type": "ORG", "scope_id": str(org_id)},
    )
    assert response.status_code == 201
    assert response.json()["scope_type"] == "ORG"
    assert response.json()["scope_id"] == str(org_id)


@pytest.mark.asyncio
async def test_branch_rejects_unpublished_source(client):
    source_id = await _create_revision(client, "Draft source")
    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Org branch", "scope_type": "ORG", "scope_id": str(uuid4())},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_org_branch_rejects_another_org_source(client, dataset_revision_store):
    source_id = UUID(await _create_revision(client, "Other org source"))
    source = dataset_revision_store[source_id]
    source.status = "published"
    source.scope_type = "ORG"
    source.scope_id = uuid4()

    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Wrong org branch", "scope_type": "ORG", "scope_id": str(uuid4())},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_project_branch_rejects_another_project_source(client, dataset_revision_store):
    source_id = UUID(await _create_revision(client, "Other project source"))
    source = dataset_revision_store[source_id]
    source.status = "published"
    source.scope_type = "PROJECT"
    source.scope_id = uuid4()

    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Wrong project branch", "scope_type": "PROJECT", "scope_id": str(uuid4())},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_org_branch_requires_owning_org_admin(client, monkeypatch, dataset_revision_store):
    import core.rbac as rbac

    source_id = UUID(await _create_revision(client, "Org role source"))
    dataset_revision_store[source_id].status = "published"
    async def no_org_admin(_db, _user_id, _org_id):
        return {rbac.GENERAL_USER}
    monkeypatch.setattr(rbac, "get_org_scoped_role_names", no_org_admin)

    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Denied org branch", "scope_type": "ORG", "scope_id": str(uuid4())},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_project_branch_requires_project_editor_or_admin(client, monkeypatch, dataset_revision_store):
    import core.rbac as rbac

    source_id = UUID(await _create_revision(client, "Project role source"))
    dataset_revision_store[source_id].status = "published"
    async def no_project_editor(_db, _user_id, project_id=None):
        return {rbac.PROJECT_VIEWER}
    monkeypatch.setattr(rbac, "get_effective_role_names", no_project_editor)

    response = await client.post(
        f"/api/dataset-revisions/{source_id}/branch",
        json={"name": "Denied project branch", "scope_type": "PROJECT", "scope_id": str(uuid4())},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_publish_requires_factor_set_and_archive_is_terminal(
    client, dataset_revision_store, emissions_factor_set_store,
):
    revision_id = UUID(await _create_revision(client, "Lifecycle revision"))
    response = await client.post(f"/api/dataset-revisions/{revision_id}/publish")
    assert response.status_code == 422
    assert dataset_revision_store[revision_id].status == "draft"

    from tests.conftest import DummyEmissionsFactorSet

    factor_set_id = uuid4()
    emissions_factor_set_store[factor_set_id] = DummyEmissionsFactorSet(
        id=factor_set_id,
        name="Test factor set",
        version="1",
        dataset_revision_id=revision_id,
    )
    response = await client.post(f"/api/dataset-revisions/{revision_id}/publish")
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    response = await client.post(f"/api/dataset-revisions/{revision_id}/deprecate")
    assert response.status_code == 200
    assert response.json()["status"] == "deprecated"
    response = await client.post(f"/api/dataset-revisions/{revision_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    response = await client.post(f"/api/dataset-revisions/{revision_id}/archive")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_bound_revision_cannot_be_unpublished_or_archived(
    client, dataset_revision_store, project_dataset_revision_store,
):
    revision_id = UUID(await _create_revision(client, "Bound lifecycle revision"))
    dataset_revision_store[revision_id].status = "published"
    project_id = uuid4()
    project_dataset_revision_store[uuid4()] = SimpleNamespace(
        project_id=project_id, dataset_revision_id=revision_id
    )

    unpublish = await client.post(
        f"/api/dataset-revisions/{revision_id}/unpublish",
        json={"confirm_bound_project_ids": [str(project_id)]},
    )
    archive = await client.post(f"/api/dataset-revisions/{revision_id}/archive")
    assert unpublish.status_code == 409
    assert archive.status_code == 409
    assert dataset_revision_store[revision_id].status == "published"


@pytest.mark.asyncio
async def test_revision_with_factor_rows_can_be_deleted(
    client, emissions_factor_set_store,
):
    revision_id = UUID(await _create_revision(client, "Retained revision"))
    from tests.conftest import DummyEmissionsFactorSet

    factor_set_id = uuid4()
    emissions_factor_set_store[factor_set_id] = DummyEmissionsFactorSet(
        id=factor_set_id,
        name="Attached factor set",
        version="1",
        dataset_revision_id=revision_id,
    )
    response = await client.delete(f"/api/dataset-revisions/{revision_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_org_lifecycle_requires_owning_org_admin(
    client, monkeypatch, dataset_revision_store,
):
    import core.rbac as rbac

    revision_id = uuid4()
    org_id = uuid4()
    from tests.conftest import DummyDatasetRevision

    dataset_revision_store[revision_id] = DummyDatasetRevision(
        id=revision_id,
        name="Org revision",
        status="draft",
        scope_type="ORG",
        scope_id=org_id,
    )
    async def no_org_admin(_db, _user_id, _org_id):
        return {rbac.GENERAL_USER}
    monkeypatch.setattr(rbac, "get_org_scoped_role_names", no_org_admin)

    bindings = await client.get(f"/api/dataset-revisions/{revision_id}/bindings")
    assert bindings.status_code == 403
    response = await client.post(f"/api/dataset-revisions/{revision_id}/publish")
    assert response.status_code == 403
    assert dataset_revision_store[revision_id].status == "draft"
