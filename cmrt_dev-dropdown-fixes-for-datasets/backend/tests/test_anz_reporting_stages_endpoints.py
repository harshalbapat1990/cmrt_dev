"""Tests for /api/anz-reporting-stages endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_anz_stages_empty(client):
    resp = await client.get("/api/anz-reporting-stages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_anz_stage(client):
    resp = await client.post("/api/anz-reporting-stages", json={"name": "Concept", "sequence": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Concept"
    assert data["sequence"] == 1
    assert "id" in data


@pytest.mark.asyncio
async def test_create_anz_stage_conflict(client):
    await client.post("/api/anz-reporting-stages", json={"name": "Design", "sequence": 2})
    resp = await client.post("/api/anz-reporting-stages", json={"name": "Design", "sequence": 3})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_anz_stage_by_id(client):
    create_resp = await client.post("/api/anz-reporting-stages", json={"name": "Construction", "sequence": 3})
    sid = create_resp.json()["id"]

    resp = await client.get(f"/api/anz-reporting-stages/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_get_anz_stage_not_found(client):
    resp = await client.get(f"/api/anz-reporting-stages/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_anz_stage(client):
    create_resp = await client.post("/api/anz-reporting-stages", json={"name": "Ops", "sequence": 4})
    sid = create_resp.json()["id"]

    resp = await client.patch(f"/api/anz-reporting-stages/{sid}", json={"sequence": 99})
    assert resp.status_code == 200
    assert resp.json()["sequence"] == 99


@pytest.mark.asyncio
async def test_patch_anz_stage_name_conflict(client):
    await client.post("/api/anz-reporting-stages", json={"name": "Alpha", "sequence": 1})
    create_resp = await client.post("/api/anz-reporting-stages", json={"name": "Beta", "sequence": 2})
    sid = create_resp.json()["id"]

    resp = await client.patch(f"/api/anz-reporting-stages/{sid}", json={"name": "Alpha"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_anz_stage_not_found(client):
    resp = await client.patch(f"/api/anz-reporting-stages/{uuid4()}", json={"sequence": 5})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_anz_stage(client):
    create_resp = await client.post("/api/anz-reporting-stages", json={"name": "Decommission", "sequence": 5})
    sid = create_resp.json()["id"]

    resp = await client.delete(f"/api/anz-reporting-stages/{sid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/anz-reporting-stages/{sid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_anz_stage_not_found(client):
    resp = await client.delete(f"/api/anz-reporting-stages/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_anz_stages_pagination(client):
    for i, name in enumerate(["S1", "S2", "S3"], start=1):
        await client.post("/api/anz-reporting-stages", json={"name": name, "sequence": i})

    resp = await client.get("/api/anz-reporting-stages?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
