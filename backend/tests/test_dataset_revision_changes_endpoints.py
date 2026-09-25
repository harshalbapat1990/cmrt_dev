"""Tests for /api/dataset-revision-changes endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


async def _create_revision(client, name: str = "Rev 1"):
    resp = await client.post("/api/dataset-revisions", json={"name": name})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_dataset_revision_change(client):
    revision_id = await _create_revision(client)
    payload = {
        "dataset_revision_id": revision_id,
        "metric_natural_key": {"grade": 1, "code": "test"},
        "change_type": "UPDATE",
    }
    resp = await client.post("/api/dataset-revision-changes", json=payload)
    assert resp.status_code == 201
    assert "id" in resp.json()


@pytest.mark.asyncio
async def test_get_dataset_revision_change_by_id(client):
    revision_id = await _create_revision(client, "Rev GetById")
    payload = {
        "dataset_revision_id": revision_id,
        "metric_natural_key": {"grade": 1, "code": "test"},
        "change_type": "ADD",
    }
    create_resp = await client.post("/api/dataset-revision-changes", json=payload)
    cid = create_resp.json()["id"]
    resp = await client.get(f"/api/dataset-revision-changes/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


@pytest.mark.asyncio
async def test_get_dataset_revision_change_not_found(client):
    resp = await client.get(f"/api/dataset-revision-changes/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_changes_by_revision(client):
    revision_id = await _create_revision(client, "Rev ListByRev")
    for ct in ["ADD", "UPDATE"]:
        await client.post(
            "/api/dataset-revision-changes",
            json={
                "dataset_revision_id": revision_id,
                "metric_natural_key": {"grade": 1, "code": ct.lower()},
                "change_type": ct,
            },
        )
    resp = await client.get(f"/api/dataset-revision-changes/by-revision/{revision_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
