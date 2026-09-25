from __future__ import annotations

from uuid import UUID

import pytest

from test_seed_data_tbls import get_test_users_data, get_test_roles_data


@pytest.fixture
def seed_test_data(user_store, role_store):
    """Seed test data with users and roles."""
    from conftest import DummyUser, DummyRole

    users_data = get_test_users_data()
    users_by_email = {}
    for data in users_data:
        user = DummyUser(**data)
        user_store[user.id] = user
        users_by_email[user.email] = user.id

    roles_data = get_test_roles_data()
    roles_by_name = {}
    for data in roles_data:
        role = DummyRole(**data)
        role_store[role.id] = role
        roles_by_name[role.name] = role.id

    return {
        "users": users_by_email,
        "roles": roles_by_name,
    }


@pytest.mark.asyncio
async def test_list_user_roles_empty(client):
    """Test listing user_roles when none exist."""
    r = await client.get("/api/user-roles?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_get_delete_user_role_flow(client, seed_test_data):
    """Test full lifecycle of user_role creation, retrieval, and deletion."""
    user_id = seed_test_data["users"]["user1@example.com"]
    role_id = seed_test_data["roles"]["Admin"]

    # create
    payload = {"user_id": str(user_id), "role_id": str(role_id), "is_active": True}
    r = await client.post("/api/user-roles", json=payload)
    assert r.status_code == 201
    body = r.json()
    user_role_id = UUID(body["id"])
    assert body["user_id"] == str(user_id)
    assert body["role_id"] == str(role_id)

    # get
    r = await client.get(f"/api/user-roles/{user_role_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(user_role_id)

    # delete
    r = await client.delete(f"/api/user-roles/{user_role_id}")
    assert r.status_code == 204

    # get again -> 404
    r = await client.get(f"/api/user-roles/{user_role_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_user_roles_all(client, seed_test_data):
    """Test listing all user_roles."""
    user_id1 = seed_test_data["users"]["user1@example.com"]
    user_id2 = seed_test_data["users"]["user2@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]

    # Create multiple user_roles
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id2),
            "role_id": str(editor_role_id),
            "is_active": True,
        },
    )

    # List all
    r = await client.get("/api/user-roles?skip=0&limit=50")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_user_roles_filter_by_user_id(client, seed_test_data):
    """Test filtering user_roles by user_id."""
    user_id1 = seed_test_data["users"]["user1@example.com"]
    user_id2 = seed_test_data["users"]["user2@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]

    # Create user_roles for different users
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id2),
            "role_id": str(editor_role_id),
            "is_active": True,
        },
    )

    # Filter by user_id1
    r = await client.get(f"/api/user-roles?user_id={user_id1}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    for item in items:
        assert UUID(item["user_id"]) == user_id1


@pytest.mark.asyncio
async def test_list_user_roles_filter_by_role_id(client, seed_test_data):
    """Test filtering user_roles by role_id."""
    user_id1 = seed_test_data["users"]["user1@example.com"]
    user_id2 = seed_test_data["users"]["user2@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]

    # Create user_roles with different roles
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id2),
            "role_id": str(editor_role_id),
            "is_active": True,
        },
    )

    # Filter by admin_role_id
    r = await client.get(f"/api/user-roles?role_id={admin_role_id}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    for item in items:
        assert UUID(item["role_id"]) == admin_role_id


@pytest.mark.asyncio
async def test_list_user_roles_filter_by_is_active(client, seed_test_data):
    """Test filtering user_roles by is_active status."""
    user_id1 = seed_test_data["users"]["user1@example.com"]
    user_id2 = seed_test_data["users"]["user2@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]

    # Create active and inactive user_roles
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id2),
            "role_id": str(editor_role_id),
            "is_active": False,
        },
    )

    # Filter for active
    r = await client.get("/api/user-roles?is_active=true")
    assert r.status_code == 200
    items = r.json()
    for item in items:
        assert item["is_active"] is True

    # Filter for inactive
    r = await client.get("/api/user-roles?is_active=false")
    assert r.status_code == 200
    items = r.json()
    for item in items:
        assert item["is_active"] is False


@pytest.mark.asyncio
async def test_list_user_roles_combined_filters(client, seed_test_data):
    """Test combining multiple filters when listing user_roles."""
    user_id1 = seed_test_data["users"]["user1@example.com"]
    user_id2 = seed_test_data["users"]["user2@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]

    # Create varying user_roles
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id1),
            "role_id": str(editor_role_id),
            "is_active": False,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id2),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )

    # Filter by user_id1 AND is_active=true
    r = await client.get(f"/api/user-roles?user_id={user_id1}&is_active=true")
    assert r.status_code == 200
    items = r.json()
    for item in items:
        assert UUID(item["user_id"]) == user_id1
        assert item["is_active"] is True


@pytest.mark.asyncio
async def test_list_user_roles_skip_limit(client, seed_test_data):
    """Test pagination with skip and limit."""
    user_id = seed_test_data["users"]["user1@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]
    editor_role_id = seed_test_data["roles"]["Editor"]
    viewer_role_id = seed_test_data["roles"]["Viewer"]

    # Create 3 user_roles for the same user
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id),
            "role_id": str(editor_role_id),
            "is_active": True,
        },
    )
    await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id),
            "role_id": str(viewer_role_id),
            "is_active": True,
        },
    )

    # Get with skip and limit
    r = await client.get(f"/api/user-roles?user_id={user_id}&skip=0&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2

    r = await client.get(f"/api/user-roles?user_id={user_id}&skip=2&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_create_user_role_with_scope(client, seed_test_data):
    """Test creating user_role with scope_type and scope_id."""
    user_id = seed_test_data["users"]["user1@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]

    # Create with scope
    from uuid import uuid4

    scope_id = uuid4()
    payload = {
        "user_id": str(user_id),
        "role_id": str(admin_role_id),
        "scope_type": "organization",
        "scope_id": str(scope_id),
        "is_active": True,
    }
    r = await client.post("/api/user-roles", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["scope_type"] == "organization"
    assert body["scope_id"] == str(scope_id)


@pytest.mark.asyncio
async def test_get_user_role_not_found(client):
    """Test retrieving a non-existent user_role returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.get(f"/api/user-roles/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_role_not_found(client):
    """Test deleting a non-existent user_role returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.delete(f"/api/user-roles/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_user_role_structure(client, seed_test_data):
    """Test that user_role response has expected structure."""
    user_id = seed_test_data["users"]["user1@example.com"]
    admin_role_id = seed_test_data["roles"]["Admin"]

    r = await client.post(
        "/api/user-roles",
        json={
            "user_id": str(user_id),
            "role_id": str(admin_role_id),
            "is_active": True,
        },
    )
    assert r.status_code == 201
    body = r.json()

    # Verify required fields
    assert "id" in body
    assert "user_id" in body
    assert "role_id" in body
    assert "is_active" in body
    assert "created_on" in body
    assert "updated_on" in body
