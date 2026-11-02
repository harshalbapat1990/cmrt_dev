"""Tests for /api/material-recycled-content endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_material_recycled_content_empty(client):
    resp = await client.get("/api/material-recycled-content")
    assert resp.status_code == 400  # revision selector is required for scoped dataset reads


@pytest.mark.asyncio
async def test_create_material_recycled_content(client):
    mid = str(uuid4())
    rf_mid = str(uuid4())
    payload = {"material_id": mid, "recycled_from_material_id": rf_mid, "percent": "0.30"}
    resp = await client.post("/api/material-recycled-content", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["material_id"] == mid
    assert "id" in data


@pytest.mark.asyncio
async def test_get_material_recycled_content_by_id(client):
    mid = str(uuid4())
    r = await client.post("/api/material-recycled-content", json={"material_id": mid})
    rid = r.json()["id"]
    resp = await client.get(f"/api/material-recycled-content/{rid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rid


@pytest.mark.asyncio
async def test_get_material_recycled_content_not_found(client):
    resp = await client.get(f"/api/material-recycled-content/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_material_recycled_content(client):
    r = await client.post("/api/material-recycled-content", json={"percent": "0.10"})
    rid = r.json()["id"]
    resp = await client.patch(f"/api/material-recycled-content/{rid}", json={"percent": "0.50"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_material_recycled_content(client):
    r = await client.post("/api/material-recycled-content", json={})
    rid = r.json()["id"]
    assert (await client.delete(f"/api/material-recycled-content/{rid}")).status_code == 204
    assert (await client.get(f"/api/material-recycled-content/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_material_recycled_content_not_found(client):
    resp = await client.delete(f"/api/material-recycled-content/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_material_recycled_content_duplicate_jurisdiction_material(client):
    """POSTing the same (jurisdiction_id, material_id) twice must return 409."""
    jur_id = str(uuid4())
    mat_id = str(uuid4())
    payload = {"jurisdiction_id": jur_id, "material_id": mat_id, "percent": "0.20"}
    first = await client.post("/api/material-recycled-content", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/material-recycled-content", json=payload)
    assert second.status_code == 409
