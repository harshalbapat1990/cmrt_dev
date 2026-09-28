"""Tests for /api/project-dataset-revisions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_PROJECT_ID = str(uuid4())
_REVISION_ID = str(uuid4())


@pytest.mark.asyncio
async def test_list_project_dataset_revisions_by_project_empty(client):
    resp = await client.get(f"/api/project-dataset-revisions/by-project/{_PROJECT_ID}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_project_dataset_revision(client):
    payload = {"project_id": _PROJECT_ID, "dataset_revision_id": _REVISION_ID}
    resp = await client.post("/api/project-dataset-revisions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["project_id"] == _PROJECT_ID
    assert data["is_locked"] is False
    assert data["calculation_report"] == {
        "missing_data": [],
        "calculation_errors": [],
        "recalculated_count": 0,
    }


@pytest.mark.asyncio
async def test_revision_switch_returns_diagnostics_and_does_not_report_success_on_failure(client, monkeypatch):
    import routers.project_dataset_revisions as pdr_router

    async def fail_recalculation(_db, _project_id, _revision_id):
        raise pdr_router.ProjectDatasetRecalculationError({
            "missing_data": [{"entry": "Drainage", "dataset_table": "Grade 2 factors"}],
            "calculation_errors": [{"entry": "Road users", "message": "factor lookup failed"}],
            "recalculated_count": 3,
        })

    monkeypatch.setattr(pdr_router, "recalculate_project_for_revision", fail_recalculation)
    response = await client.post(
        "/api/project-dataset-revisions",
        json={"project_id": str(uuid4()), "dataset_revision_id": str(uuid4())},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "dataset_recalculation_failed"
    assert detail["missing_data"][0]["dataset_table"] == "Grade 2 factors"
    assert detail["calculation_errors"][0]["message"] == "factor lookup failed"


@pytest.mark.asyncio
async def test_get_project_dataset_revision_by_id(client):
    payload = {"project_id": _PROJECT_ID, "dataset_revision_id": _REVISION_ID}
    create_resp = await client.post("/api/project-dataset-revisions", json=payload)
    pdr_id = create_resp.json()["id"]
    resp = await client.get(f"/api/project-dataset-revisions/{pdr_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pdr_id


@pytest.mark.asyncio
async def test_get_project_dataset_revision_not_found(client):
    resp = await client.get(f"/api/project-dataset-revisions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_project_dataset_revisions_by_project(client):
    project_id = str(uuid4())
    rev2 = str(uuid4())
    for rev_id in (str(uuid4()), rev2):
        await client.post(
            "/api/project-dataset-revisions",
            json={"project_id": project_id, "dataset_revision_id": rev_id},
        )
    resp = await client.get(f"/api/project-dataset-revisions/by-project/{project_id}")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["dataset_revision_id"] == rev2


@pytest.mark.asyncio
async def test_patch_project_dataset_revision_lock(client):
    payload = {"project_id": _PROJECT_ID, "dataset_revision_id": _REVISION_ID}
    create_resp = await client.post("/api/project-dataset-revisions", json=payload)
    pdr_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/project-dataset-revisions/{pdr_id}", json={"is_locked": True})
    assert resp.status_code == 200
    assert resp.json()["is_locked"] is True


@pytest.mark.asyncio
async def test_patch_project_dataset_revision_not_found(client):
    resp = await client.patch(f"/api/project-dataset-revisions/{uuid4()}", json={"is_locked": True})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_dataset_revision(client):
    payload = {"project_id": _PROJECT_ID, "dataset_revision_id": _REVISION_ID}
    create_resp = await client.post("/api/project-dataset-revisions", json=payload)
    pdr_id = create_resp.json()["id"]
    assert (await client.delete(f"/api/project-dataset-revisions/{pdr_id}")).status_code == 204
    assert (await client.get(f"/api/project-dataset-revisions/{pdr_id}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_project_dataset_revision_not_found(client):
    resp = await client.delete(f"/api/project-dataset-revisions/{uuid4()}")
    assert resp.status_code == 404
