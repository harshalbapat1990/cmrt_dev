"""Tests for /api/jurisdictions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_list_jurisdictions_empty(client):
    resp = await client.get("/api/jurisdictions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_jurisdiction(client):
    resp = await client.post("/api/jurisdictions", json={"name": "Victoria"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Victoria"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_jurisdiction_conflict(client):
    await client.post("/api/jurisdictions", json={"name": "NSW"})
    resp = await client.post("/api/jurisdictions", json={"name": "NSW"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_jurisdiction_by_id(client):
    create_resp = await client.post("/api/jurisdictions", json={"name": "Queensland"})
    jid = create_resp.json()["id"]

    resp = await client.get(f"/api/jurisdictions/{jid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == jid


@pytest.mark.asyncio
async def test_get_jurisdiction_not_found(client):
    resp = await client.get(f"/api/jurisdictions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_jurisdiction(client):
    create_resp = await client.post("/api/jurisdictions", json={"name": "Tasmania"})
    jid = create_resp.json()["id"]

    resp = await client.patch(f"/api/jurisdictions/{jid}", json={"name": "Tasmania Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Tasmania Updated"


@pytest.mark.asyncio
async def test_patch_jurisdiction_name_conflict(client):
    await client.post("/api/jurisdictions", json={"name": "SA"})
    create_resp = await client.post("/api/jurisdictions", json={"name": "WA"})
    jid = create_resp.json()["id"]

    resp = await client.patch(f"/api/jurisdictions/{jid}", json={"name": "SA"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_jurisdiction_not_found(client):
    resp = await client.patch(f"/api/jurisdictions/{uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_jurisdiction(client):
    create_resp = await client.post("/api/jurisdictions", json={"name": "ACT"})
    jid = create_resp.json()["id"]

    resp = await client.delete(f"/api/jurisdictions/{jid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/jurisdictions/{jid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_jurisdiction_not_found(client):
    resp = await client.delete(f"/api/jurisdictions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jurisdictions_pagination(client):
    for name in ["A", "B", "C"]:
        await client.post("/api/jurisdictions", json={"name": name})

    resp = await client.get("/api/jurisdictions?skip=1&limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_nested_reporting_stages_empty(client):
    create_resp = await client.post("/api/jurisdictions", json={"name": "NT"})
    jid = create_resp.json()["id"]

    resp = await client.get(f"/api/jurisdictions/{jid}/reporting-stages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_nested_reporting_stages_not_found(client):
    resp = await client.get(f"/api/jurisdictions/{uuid4()}/reporting-stages")
    assert resp.status_code == 404
