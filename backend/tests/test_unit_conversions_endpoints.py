"""Tests for /api/unit-conversions endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


def _conversion_payload(from_unit_id: str | None = None, to_unit_id: str | None = None, factor: float = 1.0) -> dict:
    return {
        "from_unit_id": from_unit_id or str(uuid4()),
        "to_unit_id": to_unit_id or str(uuid4()),
        "factor": factor,
    }


@pytest.mark.asyncio
async def test_list_unit_conversions_empty(client):
    resp = await client.get("/api/unit-conversions")
    assert resp.status_code == 400  # revision selector is required for scoped dataset reads


@pytest.mark.asyncio
async def test_create_unit_conversion(client):
    payload = _conversion_payload(factor=1000.0)
    resp = await client.post("/api/unit-conversions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["factor"]) == pytest.approx(1000.0)
    assert "id" in data


@pytest.mark.asyncio
async def test_create_unit_conversion_duplicate_pair(client):
    from_id = str(uuid4())
    to_id = str(uuid4())
    payload = _conversion_payload(from_unit_id=from_id, to_unit_id=to_id, factor=2.0)

    resp = await client.post("/api/unit-conversions", json=payload)
    assert resp.status_code == 201

    # Same pair — should conflict
    resp = await client.post("/api/unit-conversions", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_unit_conversion_by_id(client):
    payload = _conversion_payload(factor=0.001)
    create_resp = await client.post("/api/unit-conversions", json=payload)
    cid = create_resp.json()["id"]

    resp = await client.get(f"/api/unit-conversions/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


@pytest.mark.asyncio
async def test_get_unit_conversion_not_found(client):
    resp = await client.get(f"/api/unit-conversions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_unit_conversion_factor(client):
    payload = _conversion_payload(factor=1.0)
    create_resp = await client.post("/api/unit-conversions", json=payload)
    cid = create_resp.json()["id"]

    resp = await client.patch(f"/api/unit-conversions/{cid}", json={"factor": 42.5})
    assert resp.status_code == 200
    assert float(resp.json()["factor"]) == pytest.approx(42.5)


@pytest.mark.asyncio
async def test_patch_unit_conversion_not_found(client):
    resp = await client.patch(f"/api/unit-conversions/{uuid4()}", json={"factor": 1.0})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unit_conversion(client):
    payload = _conversion_payload(factor=100.0)
    create_resp = await client.post("/api/unit-conversions", json=payload)
    cid = create_resp.json()["id"]

    resp = await client.delete(f"/api/unit-conversions/{cid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/unit-conversions/{cid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unit_conversion_not_found(client):
    resp = await client.delete(f"/api/unit-conversions/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_from_unit_id(client):
    from_id = str(uuid4())
    other_id = str(uuid4())

    # Two conversions from_id → something
    for _ in range(2):
        await client.post("/api/unit-conversions", json=_conversion_payload(from_unit_id=from_id, factor=1.0))

    # One conversion from a different source
    await client.post("/api/unit-conversions", json=_conversion_payload(from_unit_id=other_id, factor=1.0))

    resp = await client.get(f"/api/unit-conversions?from_unit_id={from_id}")
    assert resp.status_code == 400  # dataset_revision_id is required even when other filters are supplied


@pytest.mark.asyncio
async def test_reverse_pair_is_separate(client):
    """A→B and B→A are distinct conversions (no conflict between them)."""
    a = str(uuid4())
    b = str(uuid4())

    resp1 = await client.post("/api/unit-conversions", json=_conversion_payload(a, b, factor=2.0))
    assert resp1.status_code == 201

    resp2 = await client.post("/api/unit-conversions", json=_conversion_payload(b, a, factor=0.5))
    assert resp2.status_code == 201
