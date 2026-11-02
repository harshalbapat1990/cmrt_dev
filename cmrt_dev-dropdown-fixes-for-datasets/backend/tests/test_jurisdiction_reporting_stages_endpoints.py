"""Tests for /api/jurisdiction-reporting-stages endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


async def _make_jurisdiction(client, name: str = "Victoria") -> str:
    resp = await client.post("/api/jurisdictions", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


def _stage_payload(jurisdiction_id: str, name: str = "Concept", sequence: int = 1) -> dict:
    return {
        "jurisdiction_id": jurisdiction_id,
        "anz_reporting_stage_id": str(uuid4()),
        "name": name,
        "sequence": sequence,
    }


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_jrs_empty(client):
    resp = await client.get("/api/jurisdiction-reporting-stages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_jrs(client):
    jid = await _make_jurisdiction(client)
    payload = _stage_payload(jid, name="Design", sequence=2)

    resp = await client.post("/api/jurisdiction-reporting-stages", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Design"
    assert data["jurisdiction_id"] == jid
    assert "id" in data


@pytest.mark.asyncio
async def test_create_jrs_unknown_jurisdiction(client):
    payload = _stage_payload(str(uuid4()))
    resp = await client.post("/api/jurisdiction-reporting-stages", json=payload)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_jrs_by_id(client):
    jid = await _make_jurisdiction(client, name="NSW")
    create_resp = await client.post("/api/jurisdiction-reporting-stages", json=_stage_payload(jid))
    sid = create_resp.json()["id"]

    resp = await client.get(f"/api/jurisdiction-reporting-stages/{sid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == sid


@pytest.mark.asyncio
async def test_get_jrs_not_found(client):
    resp = await client.get(f"/api/jurisdiction-reporting-stages/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_jrs(client):
    jid = await _make_jurisdiction(client, name="QLD")
    create_resp = await client.post("/api/jurisdiction-reporting-stages", json=_stage_payload(jid))
    sid = create_resp.json()["id"]

    resp = await client.patch(f"/api/jurisdiction-reporting-stages/{sid}", json={"sequence": 99})
    assert resp.status_code == 200
    assert resp.json()["sequence"] == 99


@pytest.mark.asyncio
async def test_patch_jrs_not_found(client):
    resp = await client.patch(f"/api/jurisdiction-reporting-stages/{uuid4()}", json={"sequence": 5})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_jrs(client):
    jid = await _make_jurisdiction(client, name="SA")
    create_resp = await client.post("/api/jurisdiction-reporting-stages", json=_stage_payload(jid))
    sid = create_resp.json()["id"]

    resp = await client.delete(f"/api/jurisdiction-reporting-stages/{sid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/jurisdiction-reporting-stages/{sid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_jrs_not_found(client):
    resp = await client.delete(f"/api/jurisdiction-reporting-stages/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nested_reporting_stages_via_jurisdictions(client):
    """GET /api/jurisdictions/{id}/reporting-stages returns stages for that jurisdiction."""
    jid = await _make_jurisdiction(client, name="WA")

    # Create two stages for this jurisdiction
    for i, name in enumerate(["S1", "S2"], start=1):
        await client.post("/api/jurisdiction-reporting-stages", json=_stage_payload(jid, name=name, sequence=i))

    # Create a stage for a different jurisdiction (should not appear)
    other_jid = await _make_jurisdiction(client, name="TAS")
    await client.post("/api/jurisdiction-reporting-stages", json=_stage_payload(other_jid, name="Other", sequence=1))

    resp = await client.get(f"/api/jurisdictions/{jid}/reporting-stages")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(item["jurisdiction_id"] == jid for item in items)
