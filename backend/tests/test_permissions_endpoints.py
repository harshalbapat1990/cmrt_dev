from __future__ import annotations

from uuid import UUID

import pytest

from test_seed_data_tbls import get_test_permissions_data


@pytest.fixture
def seed_permissions(permission_store):
    """Seed the permission store with default permissions."""
    from conftest import DummyPermission
    
    perms_data = get_test_permissions_data()
    for data in perms_data:
        perm = DummyPermission(**data)
        permission_store[perm.id] = perm
    return permission_store


@pytest.mark.asyncio
async def test_list_permissions_empty(client):
    """Test listing permissions when none exist."""
    r = await client.get("/api/permissions?skip=0&limit=50")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_permissions_with_seed(client, seed_permissions):
    """Test listing permissions after seeding."""
    r = await client.get("/api/permissions?skip=0&limit=50")
    assert r.status_code == 200
    permissions = r.json()
    assert len(permissions) >= 5
    names = {perm["name"] for perm in permissions}
    assert "create_any" in names
    assert "read_any" in names
    assert "update_any" in names
    assert "delete_any" in names
    assert "read_own" in names


@pytest.mark.asyncio
async def test_list_permissions_skip_limit(client, seed_permissions):
    """Test pagination with skip and limit."""
    r = await client.get("/api/permissions?skip=0&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2

    r = await client.get("/api/permissions?skip=2&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2


@pytest.mark.asyncio
async def test_get_permission_by_id(client, seed_permissions):
    """Test retrieving a single permission by ID."""
    # First, list to get a permission ID
    r = await client.get("/api/permissions?skip=0&limit=1")
    assert r.status_code == 200
    assert len(r.json()) > 0
    permission_id = UUID(r.json()[0]["id"])

    # Now get that specific permission
    r = await client.get(f"/api/permissions/{permission_id}")
    assert r.status_code == 200
    perm = r.json()
    assert perm["id"] == str(permission_id)
    assert "name" in perm
    assert "description" in perm


@pytest.mark.asyncio
async def test_get_permission_not_found(client):
    """Test retrieving a non-existent permission returns 404."""
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    r = await client.get(f"/api/permissions/{fake_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_permissions_large_limit(client, seed_permissions):
    """Test listing with a large limit parameter."""
    r = await client.get("/api/permissions?skip=0&limit=500")
    assert r.status_code == 200
    permissions = r.json()
    # Should have at least our seeded permissions
    assert len(permissions) >= 5


@pytest.mark.asyncio
async def test_permission_structure(client, seed_permissions):
    """Test that permission response has the expected structure."""
    r = await client.get("/api/permissions?skip=0&limit=1")
    assert r.status_code == 200
    perm = r.json()[0]

    # Verify required fields
    assert "id" in perm
    assert "name" in perm
    assert "created_on" in perm
    assert "updated_on" in perm
    assert "description" in perm

    # Verify ID is a valid UUID string
    try:
        UUID(perm["id"])
    except ValueError:
        pytest.fail(f"Permission ID is not a valid UUID: {perm['id']}")


@pytest.mark.asyncio
async def test_list_permissions_multiple_pages(client, seed_permissions):
    """Test retrieving multiple pages of permissions."""
    # Get first page
    r1 = await client.get("/api/permissions?skip=0&limit=2")
    assert r1.status_code == 200
    page1 = r1.json()
    assert len(page1) == 2

    # Get second page
    r2 = await client.get("/api/permissions?skip=2&limit=2")
    assert r2.status_code == 200
    page2 = r2.json()
    assert len(page2) == 2

    # Verify pages are different
    page1_ids = {p["id"] for p in page1}
    page2_ids = {p["id"] for p in page2}
    assert page1_ids != page2_ids
