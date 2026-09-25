"""Tests for /api/default-waste-rates endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_j1 = str(uuid4())
_m1 = str(uuid4())
_wt1 = str(uuid4())


@pytest.mark.asyncio
async def test_list_default_waste_rates_empty(client):
    resp = await client.get("/api/default-waste-rates")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_default_waste_rate(client):
    payload = {
        "jurisdiction_id": _j1,
        "material_id": _m1,
        "waste_treatment_id": _wt1,
        "basis": "by_mass",
        "rate": "0.05",
    }
    resp = await client.post("/api/default-waste-rates", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["basis"] == "by_mass"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_default_waste_rate_by_id(client):
    r = await client.post("/api/default-waste-rates", json={
        "jurisdiction_id": _j1, "material_id": _m1, "waste_treatment_id": _wt1,
        "basis": "by_volume", "rate": "0.02"
    })
    rid = r.json()["id"]
    resp = await client.get(f"/api/default-waste-rates/{rid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_default_waste_rate_not_found(client):
    resp = await client.get(f"/api/default-waste-rates/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_default_waste_rate(client):
    r = await client.post("/api/default-waste-rates", json={
        "jurisdiction_id": _j1, "material_id": _m1, "waste_treatment_id": _wt1,
        "basis": "flat", "rate": "1.0"
    })
    rid = r.json()["id"]
    resp = await client.patch(f"/api/default-waste-rates/{rid}", json={"rate": "2.0"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_default_waste_rate(client):
    r = await client.post("/api/default-waste-rates", json={
        "jurisdiction_id": _j1, "material_id": _m1, "waste_treatment_id": _wt1,
        "basis": "percentage", "rate": "0.10"
    })
    rid = r.json()["id"]
    assert (await client.delete(f"/api/default-waste-rates/{rid}")).status_code == 204
    assert (await client.get(f"/api/default-waste-rates/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_default_waste_rate_not_found(client):
    resp = await client.delete(f"/api/default-waste-rates/{uuid4()}")
    assert resp.status_code == 404
