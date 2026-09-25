"""Tests for /api/base-case-assumptions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_cat_id = str(uuid4())
_cat_id2 = str(uuid4())


@pytest.mark.asyncio
async def test_list_base_case_assumptions_empty(client):
    resp = await client.get("/api/base-case-assumptions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_base_case_assumption(client):
    resp = await client.post("/api/base-case-assumptions",
                             json={"name": "Diesel factor", "emissions_category_id": _cat_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Diesel factor"
    assert data["emissions_category_id"] == _cat_id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_base_case_assumption_duplicate(client):
    payload = {"name": "Grid emission factor", "emissions_category_id": _cat_id}
    await client.post("/api/base-case-assumptions", json=payload)
    resp = await client.post("/api/base-case-assumptions", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_base_case_assumption_by_id(client):
    r = await client.post("/api/base-case-assumptions",
                          json={"name": "LPG factor", "emissions_category_id": _cat_id2})
    aid = r.json()["id"]
    resp = await client.get(f"/api/base-case-assumptions/{aid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_base_case_assumption_not_found(client):
    resp = await client.get(f"/api/base-case-assumptions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_base_case_assumption(client):
    r = await client.post("/api/base-case-assumptions",
                          json={"name": "Solar PV", "emissions_category_id": _cat_id})
    aid = r.json()["id"]
    resp = await client.patch(f"/api/base-case-assumptions/{aid}", json={"default_value": "3.5"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_base_case_assumption(client):
    r = await client.post("/api/base-case-assumptions",
                          json={"name": "Wind factor", "emissions_category_id": _cat_id})
    aid = r.json()["id"]
    assert (await client.delete(f"/api/base-case-assumptions/{aid}")).status_code == 204
    assert (await client.get(f"/api/base-case-assumptions/{aid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_base_case_assumption_not_found(client):
    resp = await client.delete(f"/api/base-case-assumptions/{uuid4()}")
    assert resp.status_code == 404
