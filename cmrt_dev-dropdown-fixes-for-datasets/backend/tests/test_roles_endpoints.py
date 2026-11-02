from __future__ import annotations

from uuid import UUID

import pytest


@pytest.mark.asyncio
async def test_list_roles_empty(client):
    """Test listing roles when none exist."""
    r = await client.get("/api/roles?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_get_patch_delete_role_flow(client):
    """Test full lifecycle of role creation, retrieval, update, and deletion."""
    # create
    payload = {"name": "Admin", "description": "Administrator role"}
    r = await client.post("/api/roles", json=payload)
    assert r.status_code == 201
    body = r.json()
    role_id = UUID(body["id"])
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]

    # get
    r = await client.get(f"/api/roles/{role_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(role_id)
    assert r.json()["name"] == "Admin"

    # patch
    r = await client.patch(
        f"/api/roles/{role_id}",
        json={"description": "Updated admin description"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Updated admin description"

    # delete
    r = await client.delete(f"/api/roles/{role_id}")
    assert r.status_code == 204

    # get again -> 404
    r = await client.get(f"/api/roles/{role_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_role_name_conflict(client):
    """Test that creating duplicate role names fails with 409 Conflict."""
    payload = {"name": "Manager"}
    r = await client.post("/api/roles", json=payload)
    assert r.status_code == 201

    r = await client.post("/api/roles", json={"name": "Manager"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_role_case_insensitive_name_conflict(client):
    """Test that role name conflicts are case-insensitive."""
    payload = {"name": "Editor"}
    r = await client.post("/api/roles", json=payload)
    assert r.status_code == 201

    r = await client.post("/api/roles", json={"name": "EDITOR"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_roles_is_active_filter(client):
    """Test filtering roles by is_active status."""
    # Create one active, one inactive
    r = await client.post(
        "/api/roles",
        json={"name": "ActiveRole", "is_active": True},
    )
    assert r.status_code == 201
    r = await client.post(
        "/api/roles",
        json={"name": "InactiveRole", "is_active": False},
    )
    assert r.status_code == 201

    r = await client.get("/api/roles?is_active=true")
    assert r.status_code == 200
    names = {role["name"] for role in r.json()}
    assert "ActiveRole" in names
    assert "InactiveRole" not in names

    r = await client.get("/api/roles?is_active=false")
    assert r.status_code == 200
    names = {role["name"] for role in r.json()}
    assert "InactiveRole" in names
    assert "ActiveRole" not in names


@pytest.mark.asyncio
async def test_list_roles_skip_limit(client):
    """Test pagination with skip and limit parameters."""
    for i in range(3):
        r = await client.post(
            "/api/roles",
            json={"name": f"Role{i}"},
        )
        assert r.status_code == 201

    r = await client.get("/api/roles?skip=1&limit=1")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Role1"


@pytest.mark.asyncio
async def test_patch_role_name_conflict(client):
    """Test that patching a role to have a duplicate name fails."""
    r1 = await client.post("/api/roles", json={"name": "RoleA"})
    assert r1.status_code == 201
    id1 = UUID(r1.json()["id"])

    r2 = await client.post("/api/roles", json={"name": "RoleB"})
    assert r2.status_code == 201
    id2 = UUID(r2.json()["id"])

    # Attempt to change role2 name to role1 name
    r = await client.patch(f"/api/roles/{id2}", json={"name": "RoleA"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_role_partial_update(client):
    """Test patching only specific role fields."""
    r = await client.post(
        "/api/roles",
        json={"name": "PartialTest", "description": "Original description", "is_active": True},
    )
    assert r.status_code == 201
    role_id = UUID(r.json()["id"])

    # Update only description
    r = await client.patch(
        f"/api/roles/{role_id}",
        json={"description": "New description"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "PartialTest"
    assert r.json()["description"] == "New description"
    assert r.json()["is_active"] is True

    # Update only is_active
    r = await client.patch(f"/api/roles/{role_id}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    assert r.json()["name"] == "PartialTest"


@pytest.mark.asyncio
async def test_get_role_not_found(client):
    """Test retrieving a non-existent role returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.get(f"/api/roles/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_role_not_found(client):
    """Test patching a non-existent role returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.patch(f"/api/roles/{fake_id}", json={"name": "Updated"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_not_found(client):
    """Test deleting a non-existent role returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.delete(f"/api/roles/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_role_with_optional_fields(client):
    """Test creating a role with no optional fields."""
    r = await client.post("/api/roles", json={"name": "MinimalRole"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "MinimalRole"
    assert body["description"] is None
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_list_roles_multiple_filters_combined(client):
    """Test combining multiple filters when listing roles."""
    # Create varied roles
    await client.post("/api/roles", json={"name": "AdminActive", "is_active": True})
    await client.post("/api/roles", json={"name": "AdminInactive", "is_active": False})
    await client.post("/api/roles", json={"name": "SuperAdmin", "is_active": True})

    # Filter by is_active=true
    r = await client.get("/api/roles?is_active=true&skip=0&limit=50")
    assert r.status_code == 200
    names = {role["name"] for role in r.json()}
    assert len([n for n in names if "Admin" in n]) >= 2
