"""Tests for /api/waste-treatments endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_waste_treatments_empty(client):
    resp = await client.get("/api/waste-treatments")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_waste_treatment(client):
    resp = await client.post("/api/waste-treatments", json={"name": "Landfill"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Landfill"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_waste_treatment_duplicate_name(client):
    await client.post("/api/waste-treatments", json={"name": "Recycling"})
    resp = await client.post("/api/waste-treatments", json={"name": "Recycling"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_waste_treatment_by_id(client):
    r = await client.post("/api/waste-treatments", json={"name": "Reuse"})
    wid = r.json()["id"]
    resp = await client.get(f"/api/waste-treatments/{wid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_waste_treatment_not_found(client):
    resp = await client.get(f"/api/waste-treatments/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_waste_treatment(client):
    r = await client.post("/api/waste-treatments", json={"name": "Composting"})
    wid = r.json()["id"]
    resp = await client.patch(f"/api/waste-treatments/{wid}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_patch_waste_treatment_name_conflict(client):
    await client.post("/api/waste-treatments", json={"name": "WTA"})
    r = await client.post("/api/waste-treatments", json={"name": "WTB"})
    wid = r.json()["id"]
    resp = await client.patch(f"/api/waste-treatments/{wid}", json={"name": "WTA"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_waste_treatment(client):
    r = await client.post("/api/waste-treatments", json={"name": "Incineration"})
    wid = r.json()["id"]
    assert (await client.delete(f"/api/waste-treatments/{wid}")).status_code == 204
    assert (await client.get(f"/api/waste-treatments/{wid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_waste_treatment_not_found(client):
    resp = await client.delete(f"/api/waste-treatments/{uuid4()}")
    assert resp.status_code == 404
