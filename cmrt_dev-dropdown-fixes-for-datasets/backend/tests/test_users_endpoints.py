from __future__ import annotations

from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_list_users_empty(client):
    r = await client.get("/api/users?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_get_patch_delete_user_flow(client):
    # create
    payload = {"email": "test.user@example.com", "username": "testuser"}
    r = await client.post("/api/users", json=payload)
    assert r.status_code == 201
    body = r.json()
    user_id = UUID(body["id"])
    assert body["email"] == payload["email"]

    # get
    r = await client.get(f"/api/users/{user_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(user_id)

    # patch
    r = await client.patch(f"/api/users/{user_id}", json={"last_name": "Smoke"})
    assert r.status_code == 200
    assert r.json()["last_name"] == "Smoke"

    # delete
    r = await client.delete(f"/api/users/{user_id}")
    assert r.status_code == 204

    # get again -> 404
    r = await client.get(f"/api/users/{user_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_user_email_conflict(client):
    payload = {"email": "dup@example.com", "username": "u1"}
    r = await client.post("/api/users", json=payload)
    assert r.status_code == 201

    r = await client.post("/api/users", json={"email": "dup@example.com", "username": "u2"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_user_invalid_email(client):
    r = await client.post("/api/users", json={"email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_users_is_active_filter(client):
    # Create one active, one inactive
    r = await client.post("/api/users", json={"email": "active@example.com", "username": "active", "is_active": True})
    assert r.status_code == 201
    r = await client.post("/api/users", json={"email": "inactive@example.com", "username": "inactive", "is_active": False})
    assert r.status_code == 201

    r = await client.get("/api/users?is_active=true")
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert emails == {"active@example.com"}

    r = await client.get("/api/users?is_active=false")
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert emails == {"inactive@example.com"}


@pytest.mark.asyncio
async def test_list_users_skip_limit(client):
    # Dict iteration preserves insertion order; our fake store list preserves that.
    for i in range(3):
        r = await client.post(
            "/api/users",
            json={"email": f"u{i}@example.com", "username": f"u{i}"},
        )
        assert r.status_code == 201

    r = await client.get("/api/users?skip=1&limit=1")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["email"] == "u1@example.com"


@pytest.mark.asyncio
async def test_patch_user_email_conflict(client):
    r1 = await client.post("/api/users", json={"email": "a@example.com", "username": "a"})
    assert r1.status_code == 201
    id1 = UUID(r1.json()["id"])

    r2 = await client.post("/api/users", json={"email": "b@example.com", "username": "b"})
    assert r2.status_code == 201
    id2 = UUID(r2.json()["id"])

    # Attempt to change user2 email to user1 email
    r = await client.patch(f"/api/users/{id2}", json={"email": "a@example.com"})
    assert r.status_code == 409
