"""Tests for /api/materials endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_cat_id = str(uuid4())


@pytest.mark.asyncio
async def test_list_materials_empty(client):
    resp = await client.get("/api/materials")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_material(client):
    resp = await client.post("/api/materials", json={"name": "Concrete", "emissions_category_id": _cat_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Concrete"
    assert data["emissions_category_id"] == _cat_id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_material_duplicate_name(client):
    await client.post("/api/materials", json={"name": "Asphalt"})
    resp = await client.post("/api/materials", json={"name": "Asphalt"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_material_by_id(client):
    create_resp = await client.post("/api/materials", json={"name": "Steel"})
    mid = create_resp.json()["id"]
    resp = await client.get(f"/api/materials/{mid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mid


@pytest.mark.asyncio
async def test_get_material_not_found(client):
    resp = await client.get(f"/api/materials/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_material(client):
    new_cat_id = str(uuid4())
    r = await client.post("/api/materials", json={"name": "Timber"})
    mid = r.json()["id"]
    resp = await client.patch(f"/api/materials/{mid}", json={"emissions_category_id": new_cat_id})
    assert resp.status_code == 200
    assert resp.json()["emissions_category_id"] == new_cat_id


@pytest.mark.asyncio
async def test_patch_material_name_conflict(client):
    await client.post("/api/materials", json={"name": "GlassA"})
    r = await client.post("/api/materials", json={"name": "GlassB"})
    mid = r.json()["id"]
    resp = await client.patch(f"/api/materials/{mid}", json={"name": "GlassA"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_material_not_found(client):
    resp = await client.patch(f"/api/materials/{uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_material(client):
    r = await client.post("/api/materials", json={"name": "Copper"})
    mid = r.json()["id"]
    resp = await client.delete(f"/api/materials/{mid}")
    assert resp.status_code == 204
    assert (await client.get(f"/api/materials/{mid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_material_not_found(client):
    resp = await client.delete(f"/api/materials/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_materials_is_active_filter(client):
    await client.post("/api/materials", json={"name": "ActiveMat", "is_active": True})
    await client.post("/api/materials", json={"name": "InactiveMat", "is_active": False})
    resp = await client.get("/api/materials?is_active=true")
    assert resp.status_code == 200
    assert all(m["is_active"] for m in resp.json())
