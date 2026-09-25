"""Tests for /api/proponent-assumption-overrides endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_org_id = str(uuid4())
_assumption_id = str(uuid4())


@pytest.mark.asyncio
async def test_list_proponent_assumption_overrides_empty(client):
    resp = await client.get("/api/proponent-assumption-overrides")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_proponent_assumption_override(client):
    payload = {
        "proponent_org_id": _org_id,
        "assumption_id": _assumption_id,
        "effective_from": "2026-01-01",
        "value": "3.5",
    }
    resp = await client.post("/api/proponent-assumption-overrides", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["proponent_org_id"] == _org_id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_proponent_assumption_override_duplicate(client):
    payload = {
        "proponent_org_id": _org_id,
        "assumption_id": _assumption_id,
        "effective_from": "2026-06-01",
    }
    await client.post("/api/proponent-assumption-overrides", json=payload)
    resp = await client.post("/api/proponent-assumption-overrides", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_proponent_assumption_override_by_id(client):
    r = await client.post("/api/proponent-assumption-overrides", json={
        "proponent_org_id": _org_id,
        "assumption_id": _assumption_id,
        "effective_from": "2025-01-01",
    })
    oid = r.json()["id"]
    resp = await client.get(f"/api/proponent-assumption-overrides/{oid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_proponent_assumption_override_not_found(client):
    resp = await client.get(f"/api/proponent-assumption-overrides/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_proponent_assumption_override(client):
    r = await client.post("/api/proponent-assumption-overrides", json={
        "proponent_org_id": _org_id,
        "assumption_id": _assumption_id,
        "effective_from": "2024-01-01",
        "value": "1.0",
    })
    oid = r.json()["id"]
    resp = await client.patch(f"/api/proponent-assumption-overrides/{oid}", json={"value": "2.5"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_proponent_assumption_override(client):
    r = await client.post("/api/proponent-assumption-overrides", json={
        "proponent_org_id": _org_id,
        "assumption_id": _assumption_id,
        "effective_from": "2023-01-01",
    })
    oid = r.json()["id"]
    assert (await client.delete(f"/api/proponent-assumption-overrides/{oid}")).status_code == 204
    assert (await client.get(f"/api/proponent-assumption-overrides/{oid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_proponent_assumption_override_not_found(client):
    resp = await client.delete(f"/api/proponent-assumption-overrides/{uuid4()}")
    assert resp.status_code == 404
