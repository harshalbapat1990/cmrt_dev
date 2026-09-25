from __future__ import annotations

from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_list_organizations_empty(client):
    r = await client.get("/api/organizations?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_get_patch_delete_organization_flow(client):
    payload = {"name": "Org A", "organization_type": "DESIGNERS", "is_active": True}

    # create
    r = await client.post("/api/organizations", json=payload)
    assert r.status_code == 201
    body = r.json()
    organization_id = UUID(body["id"])
    assert body["name"] == payload["name"]
    assert body["organization_type"] == payload["organization_type"]
    assert body["is_active"] is True

    # get
    r = await client.get(f"/api/organizations/{organization_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(organization_id)

    # patch
    r = await client.patch(
        f"/api/organizations/{organization_id}",
        json={"name": "Org A Renamed", "organization_type": "CONTRACTORS", "is_active": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Org A Renamed"
    assert body["organization_type"] == "CONTRACTORS"
    assert body["is_active"] is False

    # delete
    r = await client.delete(f"/api/organizations/{organization_id}")
    assert r.status_code == 204

    # get again -> 404
    r = await client.get(f"/api/organizations/{organization_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_organization_name_conflict(client):
    r = await client.post(
        "/api/organizations",
        json={"name": "Dup Org", "organization_type": "DESIGNERS"},
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/organizations",
        json={"name": "dup org", "organization_type": "CONTRACTORS"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_organizations_filters(client):
    await client.post(
        "/api/organizations",
        json={"name": "Alpha Design", "organization_type": "DESIGNERS", "is_active": True},
    )
    await client.post(
        "/api/organizations",
        json={"name": "Beta Build", "organization_type": "CONTRACTORS", "is_active": False},
    )

    r = await client.get("/api/organizations?is_active=true")
    assert r.status_code == 200
    assert {o["name"] for o in r.json()} == {"Alpha Design"}

    r = await client.get("/api/organizations?is_active=false")
    assert r.status_code == 200
    assert {o["name"] for o in r.json()} == {"Beta Build"}

    r = await client.get("/api/organizations?organization_type=DESIGNERS")
    assert r.status_code == 200
    assert {o["name"] for o in r.json()} == {"Alpha Design"}

    r = await client.get("/api/organizations?q=beta")
    assert r.status_code == 200
    assert {o["name"] for o in r.json()} == {"Beta Build"}
