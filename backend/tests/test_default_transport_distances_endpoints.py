"""Tests for /api/default-transport-distances endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest

_j1 = str(uuid4())
_j2 = str(uuid4())
_mat1 = str(uuid4())
_mat2 = str(uuid4())
_cat1 = str(uuid4())

_TRUCK_PAYLOAD = {
    "truck_distance": "80",
    "rail_distance": "0",
    "sea_distance": "0",
    "truck_transport_mode": "Articulated Truck",
    "rail_transport_mode": "Rail, Bulk Transport",
    "sea_transport_mode": "Shipping",
    "source": "Test source",
}


@pytest.mark.asyncio
async def test_list_default_transport_distances_empty(client):
    resp = await client.get("/api/default-transport-distances")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_default_transport_distance(client):
    payload = {"material_id": _mat1, "jurisdiction_id": _j1, **_TRUCK_PAYLOAD}
    resp = await client.post("/api/default-transport-distances", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["material_id"] == _mat1
    assert data["truck_distance"] == "80"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_default_transport_distance_duplicate(client):
    payload = {"material_id": _mat2, "jurisdiction_id": _j1, **_TRUCK_PAYLOAD}
    await client.post("/api/default-transport-distances", json=payload)
    resp = await client.post("/api/default-transport-distances", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_default_transport_distance_by_category(client):
    payload = {"emissions_category_id": _cat1, "jurisdiction_id": _j1, **_TRUCK_PAYLOAD}
    resp = await client.post("/api/default-transport-distances", json=payload)
    assert resp.status_code == 201
    assert resp.json()["emissions_category_id"] == _cat1


@pytest.mark.asyncio
async def test_get_default_transport_distance_by_id(client):
    r = await client.post("/api/default-transport-distances",
                          json={"material_id": str(uuid4()), "jurisdiction_id": _j1, **_TRUCK_PAYLOAD})
    rid = r.json()["id"]
    resp = await client.get(f"/api/default-transport-distances/{rid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_default_transport_distance_not_found(client):
    resp = await client.get(f"/api/default-transport-distances/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_default_transport_distance(client):
    r = await client.post("/api/default-transport-distances",
                          json={"material_id": str(uuid4()), "jurisdiction_id": _j2, **_TRUCK_PAYLOAD})
    rid = r.json()["id"]
    resp = await client.patch(f"/api/default-transport-distances/{rid}", json={"truck_distance": "150"})
    assert resp.status_code == 200
    assert resp.json()["truck_distance"] == "150"


@pytest.mark.asyncio
async def test_delete_default_transport_distance(client):
    r = await client.post("/api/default-transport-distances",
                          json={"material_id": str(uuid4()), "jurisdiction_id": _j2, **_TRUCK_PAYLOAD})
    rid = r.json()["id"]
    assert (await client.delete(f"/api/default-transport-distances/{rid}")).status_code == 204
    assert (await client.get(f"/api/default-transport-distances/{rid}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_default_transport_distance_not_found(client):
    resp = await client.delete(f"/api/default-transport-distances/{uuid4()}")
    assert resp.status_code == 404
