"""Tests for /api/units endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_units_empty(client):
    resp = await client.get("/api/units")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_unit(client):
    resp = await client.post("/api/units", json={"code": "kg"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "kg"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_unit_duplicate_code(client):
    await client.post("/api/units", json={"code": "tonne"})
    resp = await client.post("/api/units", json={"code": "tonne"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_unit_by_id(client):
    create_resp = await client.post("/api/units", json={"code": "km"})
    uid = create_resp.json()["id"]

    resp = await client.get(f"/api/units/{uid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == uid
    assert resp.json()["code"] == "km"


@pytest.mark.asyncio
async def test_get_unit_not_found(client):
    resp = await client.get(f"/api/units/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_unit_code(client):
    create_resp = await client.post("/api/units", json={"code": "MJ"})
    uid = create_resp.json()["id"]

    resp = await client.patch(f"/api/units/{uid}", json={"code": "GJ"})
    assert resp.status_code == 200
    assert resp.json()["code"] == "GJ"


@pytest.mark.asyncio
async def test_patch_unit_code_conflict(client):
    await client.post("/api/units", json={"code": "L"})
    create_resp = await client.post("/api/units", json={"code": "mL"})
    uid = create_resp.json()["id"]

    resp = await client.patch(f"/api/units/{uid}", json={"code": "L"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_unit_not_found(client):
    resp = await client.patch(f"/api/units/{uuid4()}", json={"code": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unit(client):
    create_resp = await client.post("/api/units", json={"code": "kWh"})
    uid = create_resp.json()["id"]

    resp = await client.delete(f"/api/units/{uid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/units/{uid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unit_not_found(client):
    resp = await client.delete(f"/api/units/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_units_pagination(client):
    for code in ["a", "b", "c", "d"]:
        await client.post("/api/units", json={"code": code})

    resp = await client.get("/api/units?skip=1&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
