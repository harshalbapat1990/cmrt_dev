"""Tests for /api/dataset-revisions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_PAYLOAD = {"name": "Austroads Benchmarks v1.0 (2026)"}


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
