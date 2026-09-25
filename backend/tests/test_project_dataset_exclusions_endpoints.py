"""Tests for /api/project-dataset-exclusions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_PROJECT_ID = str(uuid4())
_METRIC_ID = str(uuid4())


@pytest.mark.asyncio
async def test_list_exclusions_by_project_empty(client):
    resp = await client.get(f"/api/project-dataset-exclusions/by-project/{_PROJECT_ID}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_project_dataset_exclusion(client):
    payload = {"project_id": _PROJECT_ID, "metric_id": _METRIC_ID}
    resp = await client.post("/api/project-dataset-exclusions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["project_id"] == _PROJECT_ID
    assert data["excluded_from_revision"] is True


@pytest.mark.asyncio
async def test_get_project_dataset_exclusion_by_id(client):
    payload = {"project_id": _PROJECT_ID, "metric_id": _METRIC_ID}
    create_resp = await client.post("/api/project-dataset-exclusions", json=payload)
    eid = create_resp.json()["id"]
    resp = await client.get(f"/api/project-dataset-exclusions/{eid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == eid


@pytest.mark.asyncio
async def test_get_project_dataset_exclusion_not_found(client):
    resp = await client.get(f"/api/project-dataset-exclusions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_exclusions_by_project(client):
    project_id = str(uuid4())
    for _ in range(3):
        await client.post(
            "/api/project-dataset-exclusions",
            json={"project_id": project_id, "metric_id": str(uuid4())},
        )
    resp = await client.get(f"/api/project-dataset-exclusions/by-project/{project_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_patch_project_dataset_exclusion(client):
    payload = {"project_id": _PROJECT_ID, "metric_id": _METRIC_ID}
    create_resp = await client.post("/api/project-dataset-exclusions", json=payload)
    eid = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/project-dataset-exclusions/{eid}", json={"reason": "Outside scope"}
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Outside scope"


@pytest.mark.asyncio
async def test_patch_project_dataset_exclusion_not_found(client):
    resp = await client.patch(
        f"/api/project-dataset-exclusions/{uuid4()}", json={"reason": "X"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_dataset_exclusion(client):
    payload = {"project_id": _PROJECT_ID, "metric_id": _METRIC_ID}
    create_resp = await client.post("/api/project-dataset-exclusions", json=payload)
    eid = create_resp.json()["id"]
    assert (await client.delete(f"/api/project-dataset-exclusions/{eid}")).status_code == 204
    assert (await client.get(f"/api/project-dataset-exclusions/{eid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_project_dataset_exclusion_not_found(client):
    resp = await client.delete(f"/api/project-dataset-exclusions/{uuid4()}")
    assert resp.status_code == 404
