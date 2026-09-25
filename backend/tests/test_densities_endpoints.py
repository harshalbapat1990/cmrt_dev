"""Tests for /api/densities endpoints."""
from uuid import UUID

from uuid import uuid4

import pytest

from tests.conftest import DummyUnit

_UNIT_ID = str(uuid4())
_DATASET_REVISION_ID = str(uuid4())
_JURISDICTION_ID = str(uuid4())


@pytest.fixture
def density_test_unit(unit_store):
    unit = DummyUnit(
        id=UUID(_UNIT_ID),
        code="kg/m3",
    )
    unit_store[unit.id] = unit
    return unit


def _payload(record_key, dataset="component", density="2400"):
    return {
        "dataset_revision_id": _DATASET_REVISION_ID,
        "jurisdiction_id": _JURISDICTION_ID,
        "dataset": dataset,
        "record_key": record_key,
        "unit_id": _UNIT_ID,
        "density": density,
    }


@pytest.mark.asyncio
async def test_list_densities_empty(client):
    resp = await client.get("/api/densities")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_density(client, density_test_unit):
    resp = await client.post("/api/densities", json=_payload("Concrete|General|Block"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["record_key"] == "Concrete|General|Block"
    assert data["dataset"] == "component"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_density_duplicate_key(client, density_test_unit):
    payload = _payload("Asphalt|Road|HMA", density="2300")
    await client.post("/api/densities", json=payload)
    resp = await client.post("/api/densities", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_density_by_id(client, density_test_unit):
    r = await client.post("/api/densities", json=_payload("Steel|Structural|Beam", density="7800"))
    did = r.json()["id"]
    resp = await client.get(f"/api/densities/{did}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_density_not_found(client, density_test_unit):
    resp = await client.get(f"/api/densities/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_density(client, density_test_unit):
    r = await client.post("/api/densities", json=_payload("Timber|Framing|MGP10", density="600"))
    did = r.json()["id"]
    resp = await client.patch(f"/api/densities/{did}", json={"density": "700"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_density(client, density_test_unit):
    r = await client.post("/api/densities", json=_payload("Glass|Flat|Float", density="2500"))
    did = r.json()["id"]
    assert (await client.delete(f"/api/densities/{did}")).status_code == 204
    assert (await client.get(f"/api/densities/{did}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_density_not_found(client, density_test_unit):
    resp = await client.delete(f"/api/densities/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_densities_filter_by_dataset(client, density_test_unit):
    await client.post("/api/densities", json=_payload("A|B|C", dataset="component"))
    await client.post("/api/densities", json=_payload("X|Y|Z", dataset="detailed"))
    resp = await client.get("/api/densities?dataset=component")
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["dataset"] == "component" for d in data)
