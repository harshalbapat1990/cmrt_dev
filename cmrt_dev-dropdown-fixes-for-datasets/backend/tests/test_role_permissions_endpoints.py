from __future__ import annotations

from uuid import UUID

import pytest

from test_seed_data_tbls import get_test_roles_data, get_test_permissions_data


@pytest.fixture
def seed_role_permission_data(role_store, permission_store):
    """Seed test data with roles and permissions."""
    from conftest import DummyRole, DummyPermission

    roles_data = get_test_roles_data()
    roles_by_name = {}
    for data in roles_data:
        role = DummyRole(**data)
        role_store[role.id] = role
        roles_by_name[role.name] = role.id

    perms_data = get_test_permissions_data()
    perms_by_name = {}
    for data in perms_data:
        perm = DummyPermission(**data)
        permission_store[perm.id] = perm
        perms_by_name[perm.name] = perm.id

    return {
        "roles": roles_by_name,
        "permissions": perms_by_name,
    }


@pytest.mark.asyncio
async def test_list_role_permissions_empty(client):
    """Test listing role_permissions when none exist."""
    r = await client.get("/api/role-permissions?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_get_delete_role_permission_flow(client, seed_role_permission_data):
    """Test full lifecycle of role_permission creation, retrieval, and deletion."""
    role_id = seed_role_permission_data["roles"]["Admin"]
    permission_id = seed_role_permission_data["permissions"]["create_any"]

    # create
    payload = {"role_id": str(role_id), "permission_id": str(permission_id)}
    r = await client.post("/api/role-permissions", json=payload)
    assert r.status_code == 201
    body = r.json()
    role_permission_id = UUID(body["id"])
    assert body["role_id"] == str(role_id)
    assert body["permission_id"] == str(permission_id)

    # get
    r = await client.get(f"/api/role-permissions/{role_permission_id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(role_permission_id)

    # delete
    r = await client.delete(f"/api/role-permissions/{role_permission_id}")
    assert r.status_code == 204

    # get again -> 404
    r = await client.get(f"/api/role-permissions/{role_permission_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_role_permissions_all(client, seed_role_permission_data):
    """Test listing all role_permissions."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    editor_role_id = seed_role_permission_data["roles"]["Editor"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]
    read_perm_id = seed_role_permission_data["permissions"]["read_any"]

    # Create multiple role_permissions
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(editor_role_id), "permission_id": str(read_perm_id)},
    )

    # List all
    r = await client.get("/api/role-permissions?skip=0&limit=50")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_role_permissions_filter_by_role_id(client, seed_role_permission_data):
    """Test filtering role_permissions by role_id."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    editor_role_id = seed_role_permission_data["roles"]["Editor"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]
    read_perm_id = seed_role_permission_data["permissions"]["read_any"]
    update_perm_id = seed_role_permission_data["permissions"]["update_any"]

    # Create role_permissions for different roles
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(update_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(editor_role_id), "permission_id": str(read_perm_id)},
    )

    # Filter by admin_role_id
    r = await client.get(f"/api/role-permissions?role_id={admin_role_id}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    for item in items:
        assert UUID(item["role_id"]) == admin_role_id


@pytest.mark.asyncio
async def test_list_role_permissions_filter_by_permission_id(client, seed_role_permission_data):
    """Test filtering role_permissions by permission_id."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    editor_role_id = seed_role_permission_data["roles"]["Editor"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]

    # Create role_permissions with the same permission
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(editor_role_id), "permission_id": str(create_perm_id)},
    )

    # Filter by create_perm_id
    r = await client.get(f"/api/role-permissions?permission_id={create_perm_id}")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    for item in items:
        assert UUID(item["permission_id"]) == create_perm_id


@pytest.mark.asyncio
async def test_list_role_permissions_combined_filters(client, seed_role_permission_data):
    """Test combining role_id and permission_id filters."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    editor_role_id = seed_role_permission_data["roles"]["Editor"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]
    read_perm_id = seed_role_permission_data["permissions"]["read_any"]

    # Create varying role_permissions
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(read_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(editor_role_id), "permission_id": str(read_perm_id)},
    )

    # Filter by admin_role_id AND create_perm_id
    r = await client.get(
        f"/api/role-permissions?role_id={admin_role_id}&permission_id={create_perm_id}"
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    for item in items:
        assert UUID(item["role_id"]) == admin_role_id
        assert UUID(item["permission_id"]) == create_perm_id


@pytest.mark.asyncio
async def test_list_role_permissions_skip_limit(client, seed_role_permission_data):
    """Test pagination with skip and limit."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]
    read_perm_id = seed_role_permission_data["permissions"]["read_any"]
    update_perm_id = seed_role_permission_data["permissions"]["update_any"]

    # Create multiple role_permissions
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(read_perm_id)},
    )
    await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(update_perm_id)},
    )

    # Get with pagination
    r = await client.get(f"/api/role-permissions?role_id={admin_role_id}&skip=0&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2

    r = await client.get(f"/api/role-permissions?role_id={admin_role_id}&skip=2&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_role_permission_not_found(client):
    """Test retrieving a non-existent role_permission returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.get(f"/api/role-permissions/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_permission_not_found(client):
    """Test deleting a non-existent role_permission returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.delete(f"/api/role-permissions/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_role_permission_structure(client, seed_role_permission_data):
    """Test that role_permission response has expected structure."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]

    r = await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    assert r.status_code == 201
    body = r.json()

    # Verify required fields
    assert "id" in body
    assert "role_id" in body
    assert "permission_id" in body
    assert "created_on" in body
    assert "updated_on" in body

    # Verify ID is a valid UUID string
    try:
        UUID(body["id"])
    except ValueError:
        pytest.fail(f"Role-Permission ID is not a valid UUID: {body['id']}")


@pytest.mark.asyncio
async def test_create_multiple_role_permissions_for_one_role(client, seed_role_permission_data):
    """Test creating multiple permissions for the same role."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]
    read_perm_id = seed_role_permission_data["permissions"]["read_any"]
    update_perm_id = seed_role_permission_data["permissions"]["update_any"]
    delete_perm_id = seed_role_permission_data["permissions"]["delete_any"]

    # Create 4 permissions for admin role
    perm_ids = [create_perm_id, read_perm_id, update_perm_id, delete_perm_id]
    created_ids = []

    for perm_id in perm_ids:
        r = await client.post(
            "/api/role-permissions",
            json={"role_id": str(admin_role_id), "permission_id": str(perm_id)},
        )
        assert r.status_code == 201
        created_ids.append(UUID(r.json()["id"]))

    # Verify all were created
    assert len(created_ids) == 4
    assert len(set(created_ids)) == 4  # All unique


@pytest.mark.asyncio
async def test_role_permission_timestamps(client, seed_role_permission_data):
    """Test that timestamps are correctly set on role_permission creation."""
    admin_role_id = seed_role_permission_data["roles"]["Admin"]
    create_perm_id = seed_role_permission_data["permissions"]["create_any"]

    r = await client.post(
        "/api/role-permissions",
        json={"role_id": str(admin_role_id), "permission_id": str(create_perm_id)},
    )
    assert r.status_code == 201
    body = r.json()

    # Verify created_on is present and updated_on is None or null
    assert body["created_on"] is not None
    assert body["updated_on"] is None
