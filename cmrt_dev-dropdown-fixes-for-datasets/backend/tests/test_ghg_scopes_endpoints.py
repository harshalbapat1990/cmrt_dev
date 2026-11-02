"""Tests for /api/ghg-scopes endpoints (read-only)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_ghg_scopes(client):
    """Store is pre-populated with Scope 1, 2, 3 in conftest."""
    resp = await client.get("/api/ghg-scopes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    ids = {item["id"] for item in data}
    assert ids == {1, 2, 3}


@pytest.mark.asyncio
async def test_get_ghg_scope_by_id(client):
    resp = await client.get("/api/ghg-scopes/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Scope 1"


@pytest.mark.asyncio
async def test_get_ghg_scope_2(client):
    resp = await client.get("/api/ghg-scopes/2")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Scope 2"


@pytest.mark.asyncio
async def test_get_ghg_scope_3(client):
    resp = await client.get("/api/ghg-scopes/3")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Scope 3"


@pytest.mark.asyncio
async def test_get_ghg_scope_not_found(client):
    resp = await client.get("/api/ghg-scopes/99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_no_post_endpoint(client):
    """GHG scopes are read-only — POST should return 405."""
    resp = await client.post("/api/ghg-scopes", json={"id": 4, "name": "Scope 4"})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_no_delete_endpoint(client):
    """GHG scopes are read-only — DELETE should return 405."""
    resp = await client.delete("/api/ghg-scopes/1")
    assert resp.status_code == 405
