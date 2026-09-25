"""Tests for /api/value-bands endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_value_bands_empty(client):
    resp = await client.get("/api/value-bands")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_value_band(client):
    resp = await client.post("/api/value-bands", json={"code": "low", "sort_order": 1})
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "low"
    assert data["sort_order"] == 1


@pytest.mark.asyncio
async def test_create_value_band_conflict(client):
    await client.post("/api/value-bands", json={"code": "mid", "sort_order": 2})
    resp = await client.post("/api/value-bands", json={"code": "mid", "sort_order": 2})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_value_band_by_code(client):
    await client.post("/api/value-bands", json={"code": "high", "sort_order": 3})
    resp = await client.get("/api/value-bands/high")
    assert resp.status_code == 200
    assert resp.json()["code"] == "high"


@pytest.mark.asyncio
async def test_get_value_band_not_found(client):
    resp = await client.get("/api/value-bands/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_value_band(client):
    await client.post("/api/value-bands", json={"code": "band_a", "sort_order": 1})
    resp = await client.patch("/api/value-bands/band_a", json={"sort_order": 10})
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 10


@pytest.mark.asyncio
async def test_patch_value_band_not_found(client):
    resp = await client.patch("/api/value-bands/no_such_code", json={"sort_order": 1})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_value_band(client):
    await client.post("/api/value-bands", json={"code": "temp_band", "sort_order": 99})
    resp = await client.delete("/api/value-bands/temp_band")
    assert resp.status_code == 204
    assert (await client.get("/api/value-bands/temp_band")).status_code == 404


@pytest.mark.asyncio
async def test_delete_value_band_not_found(client):
    resp = await client.delete("/api/value-bands/no_such_code")
    assert resp.status_code == 404
