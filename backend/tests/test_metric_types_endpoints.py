"""Tests for /api/metric-types endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_PAYLOAD = {"code": "emission_intensity_a1_a3", "name": "Emission Intensity A1-A3"}


@pytest.mark.asyncio
async def test_list_metric_types_empty(client):
    resp = await client.get("/api/metric-types")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_metric_type(client):
    resp = await client.post("/api/metric-types", json=_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == _PAYLOAD["code"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_metric_type_conflict(client):
    await client.post("/api/metric-types", json=_PAYLOAD)
    resp = await client.post("/api/metric-types", json=_PAYLOAD)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_metric_type_by_id(client):
    create_resp = await client.post("/api/metric-types", json=_PAYLOAD)
    mid = create_resp.json()["id"]
    resp = await client.get(f"/api/metric-types/{mid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mid


@pytest.mark.asyncio
async def test_get_metric_type_not_found(client):
    resp = await client.get(f"/api/metric-types/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_metric_type_by_code(client):
    await client.post("/api/metric-types", json=_PAYLOAD)
    resp = await client.get(f"/api/metric-types/by-code/{_PAYLOAD['code']}")
    assert resp.status_code == 200
    assert resp.json()["code"] == _PAYLOAD["code"]


@pytest.mark.asyncio
async def test_get_metric_type_by_code_not_found(client):
    resp = await client.get("/api/metric-types/by-code/no_such_code")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_metric_type(client):
    create_resp = await client.post("/api/metric-types", json=_PAYLOAD)
    mid = create_resp.json()["id"]
    resp = await client.patch(f"/api/metric-types/{mid}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_patch_metric_type_not_found(client):
    resp = await client.patch(f"/api/metric-types/{uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_metric_type(client):
    create_resp = await client.post("/api/metric-types", json=_PAYLOAD)
    mid = create_resp.json()["id"]
    assert (await client.delete(f"/api/metric-types/{mid}")).status_code == 204
    assert (await client.get(f"/api/metric-types/{mid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_metric_type_not_found(client):
    resp = await client.delete(f"/api/metric-types/{uuid4()}")
    assert resp.status_code == 404
