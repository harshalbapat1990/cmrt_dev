"""Tests for /api/emissions-categories endpoints."""
from __future__ import annotations

from uuid import uuid4

import pytest


def _cat_payload(
    name: str = "Stationary Energy",
    code: str = "S1",
    scope: int = 1,
    parent_category_id: str | None = None,
    is_active: bool = True,
) -> dict:
    payload: dict = {"name": name, "code": code, "scope": scope, "is_active": is_active}
    if parent_category_id is not None:
        payload["parent_category_id"] = parent_category_id
    return payload


@pytest.mark.asyncio
async def test_list_emissions_categories_empty(client):
    resp = await client.get("/api/emissions-categories")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_emissions_category(client):
    resp = await client.post("/api/emissions-categories", json=_cat_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Stationary Energy"
    assert data["scope"] == 1
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_get_emissions_category_by_id(client):
    create_resp = await client.post("/api/emissions-categories", json=_cat_payload(name="Transport", code="T1"))
    cid = create_resp.json()["id"]

    resp = await client.get(f"/api/emissions-categories/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid
    assert resp.json()["name"] == "Transport"


@pytest.mark.asyncio
async def test_get_emissions_category_not_found(client):
    resp = await client.get(f"/api/emissions-categories/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_emissions_category(client):
    create_resp = await client.post("/api/emissions-categories", json=_cat_payload(name="Waste", code="W1"))
    cid = create_resp.json()["id"]

    resp = await client.patch(f"/api/emissions-categories/{cid}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_patch_emissions_category_not_found(client):
    resp = await client.patch(f"/api/emissions-categories/{uuid4()}", json={"is_active": False})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_emissions_category(client):
    create_resp = await client.post("/api/emissions-categories", json=_cat_payload(name="IPPU", code="IP1"))
    cid = create_resp.json()["id"]

    resp = await client.delete(f"/api/emissions-categories/{cid}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/emissions-categories/{cid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_emissions_category_not_found(client):
    resp = await client.delete(f"/api/emissions-categories/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_is_active(client):
    await client.post("/api/emissions-categories", json=_cat_payload(name="Active Cat", code="AC1", is_active=True))
    await client.post("/api/emissions-categories", json=_cat_payload(name="Inactive Cat", code="IC1", is_active=False))

    resp = await client.get("/api/emissions-categories?is_active=true")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["name"] == "Active Cat"

    resp = await client.get("/api/emissions-categories?is_active=false")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["name"] == "Inactive Cat"


@pytest.mark.asyncio
async def test_filter_by_scope(client):
    await client.post("/api/emissions-categories", json=_cat_payload(name="Scope1 Cat", code="SC1", scope=1))
    await client.post("/api/emissions-categories", json=_cat_payload(name="Scope2 Cat", code="SC2", scope=2))
    await client.post("/api/emissions-categories", json=_cat_payload(name="Scope3 Cat", code="SC3", scope=3))

    resp = await client.get("/api/emissions-categories?scope=2")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["scope"] == 2


@pytest.mark.asyncio
async def test_filter_top_level_only(client):
    # Create two top-level categories (no parent)
    r1 = await client.post("/api/emissions-categories", json=_cat_payload(name="TopA", code="TA1"))
    r2 = await client.post("/api/emissions-categories", json=_cat_payload(name="TopB", code="TB1"))
    parent_id = r1.json()["id"]

    # Create a child of TopA
    await client.post(
        "/api/emissions-categories",
        json=_cat_payload(name="ChildA", code="CA1", parent_category_id=parent_id),
    )

    resp = await client.get("/api/emissions-categories?top_level_only=true")
    assert resp.status_code == 200
    items = resp.json()
    ids = {item["id"] for item in items}
    assert r1.json()["id"] in ids
    assert r2.json()["id"] in ids
    # Child should NOT appear
    assert all(item.get("parent_category_id") is None for item in items)


@pytest.mark.asyncio
async def test_filter_by_parent_category_id(client):
    parent_resp = await client.post("/api/emissions-categories", json=_cat_payload(name="Parent", code="P1"))
    parent_id = parent_resp.json()["id"]

    # Two children
    await client.post(
        "/api/emissions-categories",
        json=_cat_payload(name="Child1", code="C1", parent_category_id=parent_id),
    )
    await client.post(
        "/api/emissions-categories",
        json=_cat_payload(name="Child2", code="C2", parent_category_id=parent_id),
    )

    # Unrelated category
    await client.post("/api/emissions-categories", json=_cat_payload(name="Unrelated", code="U1"))

    resp = await client.get(f"/api/emissions-categories?parent_category_id={parent_id}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(item["parent_category_id"] == parent_id for item in items)


@pytest.mark.asyncio
async def test_get_children_of_category(client):
    parent_resp = await client.post("/api/emissions-categories", json=_cat_payload(name="ParentX", code="PX"))
    parent_id = parent_resp.json()["id"]

    # Two children
    for i in range(2):
        await client.post(
            "/api/emissions-categories",
            json=_cat_payload(name=f"Child{i}", code=f"CX{i}", parent_category_id=parent_id),
        )

    resp = await client.get(f"/api/emissions-categories/{parent_id}/children")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert all(item["parent_category_id"] == parent_id for item in items)


@pytest.mark.asyncio
async def test_get_children_parent_not_found(client):
    resp = await client.get(f"/api/emissions-categories/{uuid4()}/children")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_emissions_categories_pagination(client):
    for i in range(5):
        await client.post("/api/emissions-categories", json=_cat_payload(name=f"Cat{i}", code=f"EC{i}"))

    resp = await client.get("/api/emissions-categories?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
