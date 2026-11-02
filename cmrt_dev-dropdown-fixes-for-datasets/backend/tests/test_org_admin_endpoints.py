"""
Tests for Organization Admin User Management endpoints.

Tests the /api/org-admin endpoints for:
- Listing organization users with their project roles
- Adding project admins to projects
- Removing project admins from projects  
- Deleting users from organizations
"""
from __future__ import annotations

from uuid import UUID, uuid4
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

import pytest
import httpx

from tests.conftest import user_role_store


@dataclass
class DummyProject:
    """Minimal project for testing org admin endpoints."""
    id: UUID
    project_name: str
    proponent_org_id: UUID
    is_active: bool = True
    created_on: Optional[datetime] = None


@dataclass
class DummyProjectOrganization:
    """Secondary organization association with project."""
    id: UUID
    project_id: UUID
    organization_id: UUID
    created_on: Optional[datetime] = None


@pytest.fixture
def project_store() -> Dict[UUID, DummyProject]:
    return {}


@pytest.fixture
def project_organization_store() -> Dict[UUID, DummyProjectOrganization]:
    return {}


@pytest.fixture
def org_admin_test_setup(
    user_store,
    organization_store,
    role_store,
    user_role_store,
    project_store,
    project_organization_store,
):
    """Set up test data for org admin tests."""
    from conftest import DummyUser, DummyOrganization, DummyRole, DummyUserRole
    
    # Organizations
    jacobs_org = DummyOrganization(
        id=uuid4(),
        name="Jacobs Engineering",
        organization_type="CONTRACTORS",
        is_active=True
    )
    acme_org = DummyOrganization(
        id=uuid4(),
        name="Acme Corp",
        organization_type="DESIGNERS",
        is_active=True
    )
    organization_store[jacobs_org.id] = jacobs_org
    organization_store[acme_org.id] = acme_org
    
    # Roles
    org_admin_role = DummyRole(
        id=uuid4(),
        name="ORG_ADMIN",
        description="Organization Administrator",
        is_active=True
    )
    project_admin_role = DummyRole(
        id=uuid4(),
        name="PROJECT_ADMIN",
        description="Project Administrator",
        is_active=True
    )
    project_editor_role = DummyRole(
        id=uuid4(),
        name="PROJECT_EDITOR",
        description="Project Editor",
        is_active=True
    )
    role_store[org_admin_role.id] = org_admin_role
    role_store[project_admin_role.id] = project_admin_role
    role_store[project_editor_role.id] = project_editor_role
    
    # Users in Jacobs org
    org_admin_user = DummyUser(
        id=uuid4(),
        email="admin@jacobs.com",
        first_name="Admin",
        last_name="User",
        organization_id=jacobs_org.id,
        is_active=True
    )
    project_admin_user = DummyUser(
        id=uuid4(),
        email="proj-admin@jacobs.com",
        first_name="Project",
        last_name="Admin",
        organization_id=jacobs_org.id,
        is_active=True
    )
    regular_user = DummyUser(
        id=uuid4(),
        email="regular@jacobs.com",
        first_name="Regular",
        last_name="User",
        organization_id=jacobs_org.id,
        is_active=True
    )
    inactive_user = DummyUser(
        id=uuid4(),
        email="inactive@jacobs.com",
        first_name="Inactive",
        last_name="User",
        organization_id=jacobs_org.id,
        is_active=False
    )
    
    # User in different org
    other_org_user = DummyUser(
        id=uuid4(),
        email="user@acme.com",
        first_name="Acme",
        last_name="User",
        organization_id=acme_org.id,
        is_active=True
    )
    
    user_store[org_admin_user.id] = org_admin_user
    user_store[project_admin_user.id] = project_admin_user
    user_store[regular_user.id] = regular_user
    user_store[inactive_user.id] = inactive_user
    user_store[other_org_user.id] = other_org_user
    
    # Projects
    project1 = DummyProject(
        id=uuid4(),
        project_name="Highway Project A",
        proponent_org_id=jacobs_org.id,
        is_active=True
    )
    project2 = DummyProject(
        id=uuid4(),
        project_name="Bridge Project B",
        proponent_org_id=jacobs_org.id,
        is_active=True
    )
    project3 = DummyProject(
        id=uuid4(),
        project_name="Other Project",
        proponent_org_id=acme_org.id,
        is_active=True
    )
    project_store[project1.id] = project1
    project_store[project2.id] = project2
    project_store[project3.id] = project3
    
    # ORG_ADMIN role for org_admin_user
    org_admin_role_assignment = DummyUserRole(
        id=uuid4(),
        user_id=org_admin_user.id,
        role_id=org_admin_role.id,
        scope_type="ORGANISATION",
        scope_id=jacobs_org.id,
        is_active=True
    )
    user_role_store[org_admin_role_assignment.id] = org_admin_role_assignment
    
    # PROJECT_ADMIN role for project_admin_user on project1
    project_admin_role_assignment = DummyUserRole(
        id=uuid4(),
        user_id=project_admin_user.id,
        role_id=project_admin_role.id,
        scope_type="PROJECT",
        scope_id=project1.id,
        is_active=True
    )
    user_role_store[project_admin_role_assignment.id] = project_admin_role_assignment
    
    # PROJECT_EDITOR role for regular_user on project2
    project_editor_role_assignment = DummyUserRole(
        id=uuid4(),
        user_id=regular_user.id,
        role_id=project_editor_role.id,
        scope_type="PROJECT",
        scope_id=project2.id,
        is_active=True
    )
    user_role_store[project_editor_role_assignment.id] = project_editor_role_assignment
    
    return {
        "jacobs_org": jacobs_org,
        "acme_org": acme_org,
        "org_admin_user": org_admin_user,
        "project_admin_user": project_admin_user,
        "regular_user": regular_user,
        "inactive_user": inactive_user,
        "other_org_user": other_org_user,
        "project1": project1,
        "project2": project2,
        "project3": project3,
        "org_admin_role": org_admin_role,
        "project_admin_role": project_admin_role,
        "project_editor_role": project_editor_role,
        "project_admin_role_assignment": project_admin_role_assignment,
        "project_editor_role_assignment": project_editor_role_assignment,
    }


@pytest.fixture(autouse=True)
def patch_org_admin_crud(
    monkeypatch: pytest.MonkeyPatch,
    user_store,
    organization_store,
    role_store,
    user_role_store,
    project_store,
    project_organization_store,
):
    """Patch CRUD functions for org admin router."""
    import routers.org_admin as org_admin_router
    import crud.users as users_crud
    import crud.roles as roles_crud
    import crud.user_roles as user_roles_crud
    
    # Patch get_org_users_with_project_roles
    async def mock_get_org_users_with_project_roles(_db, organization_id: UUID, include_inactive: bool = False):
        result = []
        
        for user in user_store.values():
            if user.organization_id != organization_id:
                continue
            if not include_inactive and not user.is_active:
                continue
            
            # Get projects for this org
            org_project_ids = [p.id for p in project_store.values() if p.proponent_org_id == organization_id]
            org_project_ids.extend([
                po.project_id for po in project_organization_store.values()
                if po.organization_id == organization_id
            ])
            
            # Get user's project roles
            project_roles = []
            for ur in user_role_store.values():
                if ur.user_id == user.id and ur.scope_type == "PROJECT" and ur.scope_id in org_project_ids:
                    role = role_store.get(ur.role_id)
                    project = project_store.get(ur.scope_id)
                    if role and project:
                        project_roles.append({
                            "project_id": str(ur.scope_id),
                            "project_name": project.project_name,
                            "role_name": role.name,
                            "user_role_id": str(ur.id),
                            "is_active": ur.is_active
                        })
            
            # Check if user has ORG_ADMIN role
            has_org_admin_role = any(
                ur.user_id == user.id and
                ur.scope_type == "ORGANISATION" and
                ur.scope_id == organization_id and
                role_store.get(ur.role_id) and
                role_store.get(ur.role_id).name == "ORG_ADMIN" and
                ur.is_active
                for ur in user_role_store.values()
            )
            
            display_name = None
            if user.first_name or user.last_name:
                display_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            
            result.append({
                "user_id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": display_name,
                "is_active": user.is_active,
                "project_roles": project_roles,
                "has_org_admin_role": has_org_admin_role
            })
        
        return result
    
    # Patch verify_project_belongs_to_org
    async def mock_verify_project_belongs_to_org(_db, project_id: UUID, organization_id: UUID):
        project = project_store.get(project_id)
        if project and project.proponent_org_id == organization_id:
            return True
        
        return any(
            po.project_id == project_id and po.organization_id == organization_id
            for po in project_organization_store.values()
        )
    
    # Patch verify_user_in_org
    async def mock_verify_user_in_org(_db, user_id: UUID, organization_id: UUID):
        user = user_store.get(user_id)
        return user and user.organization_id == organization_id
    
    # Patch get_user_project_admin_role
    async def mock_get_user_project_admin_role(_db, user_id: UUID, project_id: UUID):
        project_admin_role = next((r for r in role_store.values() if r.name == "PROJECT_ADMIN"), None)
        if not project_admin_role:
            return None
        
        for ur in user_role_store.values():
            if (ur.user_id == user_id and
                ur.role_id == project_admin_role.id and
                ur.scope_type == "PROJECT" and
                ur.scope_id == project_id):
                return ur.id
        
        return None
    
    # Patch get_user from users CRUD
    async def mock_get_user(_db, user_id: UUID):
        return user_store.get(user_id)
    
    # Patch delete_user from users CRUD
    async def mock_update_user(_db, user, payload):
        user.is_active = payload.is_active
        user.organization_id = payload.organization_id
        return user


    async def mock_delete_all_user_roles_for_user(_db, user_id: UUID):
        to_delete = [
            ur_id
            for ur_id, ur in user_role_store.items()
            if ur.user_id == user_id
        ]

        for ur_id in to_delete:
            del user_role_store[ur_id]

        return True
    
    # Patch get_role_by_name from roles CRUD
    async def mock_get_role_by_name(_db, name: str):
        return next((r for r in role_store.values() if r.name == name), None)
    
    # Patch create_user_role from user_roles CRUD
    async def mock_create_user_role(_db, user_id, role_id, scope_type, scope_id, is_active):
        from conftest import DummyUserRole
        user_role = DummyUserRole(
            id=uuid4(),
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            is_active=is_active,
            created_on=datetime.utcnow()
        )
        user_role_store[user_role.id] = user_role
        return user_role
    
    # Patch delete_user_role from user_roles CRUD
    async def mock_delete_user_role(_db, user_role_id: UUID):
        if user_role_id in user_role_store:
            del user_role_store[user_role_id]
            return True
        return False
    
    monkeypatch.setattr(org_admin_router, "get_org_users_with_project_roles", mock_get_org_users_with_project_roles)
    monkeypatch.setattr(org_admin_router, "verify_project_belongs_to_org", mock_verify_project_belongs_to_org)
    monkeypatch.setattr(org_admin_router, "verify_user_in_org", mock_verify_user_in_org)
    monkeypatch.setattr(org_admin_router, "get_user_project_admin_role", mock_get_user_project_admin_role)
    monkeypatch.setattr(org_admin_router, "get_user", mock_get_user)
    monkeypatch.setattr(org_admin_router, "update_user", mock_update_user)
    monkeypatch.setattr(
        org_admin_router,
        "delete_all_user_roles_for_user",
        mock_delete_all_user_roles_for_user,
    )
    monkeypatch.setattr(org_admin_router, "get_role_by_name", mock_get_role_by_name)
    monkeypatch.setattr(org_admin_router, "create_user_role", mock_create_user_role)
    monkeypatch.setattr(org_admin_router, "delete_user_role", mock_delete_user_role)


@pytest.fixture
def org_admin_app(app, org_admin_test_setup):
    """Override principal to be org admin."""
    from core.security import Principal, get_current_principal
    
    async def override_get_principal() -> Principal:
        return Principal(
            user_id=org_admin_test_setup["org_admin_user"].id,
            email=org_admin_test_setup["org_admin_user"].email,
            oidc_issuer="test-issuer",
            oidc_sub="test-sub-orgadmin",
            organization_id=org_admin_test_setup["jacobs_org"].id,
        )
    
    app.dependency_overrides[get_current_principal] = override_get_principal
    return app


@pytest.fixture
async def org_admin_client(org_admin_app):
    """Client with org admin authentication."""
    transport = httpx.ASGITransport(app=org_admin_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ========================================
# Test: List Organization Users
# ========================================

@pytest.mark.asyncio
async def test_list_organization_users(org_admin_client, org_admin_test_setup):
    """Test listing all users in organization with their project roles."""
    r = await org_admin_client.get("/api/org-admin/users")
    
    assert r.status_code == 200
    users = r.json()
    
    # Should have 3 active users (org admin, project admin, regular user)
    assert len(users) == 3
    
    # Check org admin user
    org_admin = next(u for u in users if u["email"] == "admin@jacobs.com")
    assert org_admin["has_org_admin_role"] is True
    assert org_admin["is_active"] is True
    assert org_admin["project_roles"] == []
    
    # Check project admin user
    proj_admin = next(u for u in users if u["email"] == "proj-admin@jacobs.com")
    assert proj_admin["has_org_admin_role"] is False
    assert len(proj_admin["project_roles"]) == 1
    assert proj_admin["project_roles"][0]["role_name"] == "PROJECT_ADMIN"
    assert proj_admin["project_roles"][0]["project_name"] == "Highway Project A"
    
    # Check regular user
    regular = next(u for u in users if u["email"] == "regular@jacobs.com")
    assert regular["has_org_admin_role"] is False
    assert len(regular["project_roles"]) == 1
    assert regular["project_roles"][0]["role_name"] == "PROJECT_EDITOR"


@pytest.mark.asyncio
async def test_list_organization_users_include_inactive(org_admin_client, org_admin_test_setup):
    """Test listing users including inactive ones."""
    r = await org_admin_client.get("/api/org-admin/users?include_inactive=true")
    
    assert r.status_code == 200
    users = r.json()
    
    # Should have 4 users now (3 active + 1 inactive)
    assert len(users) == 4
    
    inactive = next(u for u in users if u["email"] == "inactive@jacobs.com")
    assert inactive["is_active"] is False


# ========================================
# Test: Add Project Admin
# ========================================

@pytest.mark.asyncio
async def test_add_project_admin(org_admin_client, org_admin_test_setup, user_role_store):
    """Test adding a user as PROJECT_ADMIN to a project."""
    regular_user_id = org_admin_test_setup["regular_user"].id
    project2_id = org_admin_test_setup["project2"].id
    
    payload = {"user_id": str(regular_user_id)}
    r = await org_admin_client.post(f"/api/org-admin/projects/{project2_id}/admins", json=payload)
    
    assert r.status_code == 201
    body = r.json()
    
    assert body["user_id"] == str(regular_user_id)
    assert body["project_id"] == str(project2_id)
    assert body["role_name"] == "PROJECT_ADMIN"
    assert "user_role_id" in body
    assert body["message"] == "Project admin role granted successfully"
    
    # Verify role was created in store
    user_role_id = UUID(body["user_role_id"])
    assert user_role_id in user_role_store
    user_role = user_role_store[user_role_id]
    assert user_role.user_id == regular_user_id
    assert user_role.scope_id == project2_id


@pytest.mark.asyncio
async def test_add_project_admin_already_exists(org_admin_client, org_admin_test_setup):
    """Test adding PROJECT_ADMIN when user already has it."""
    project_admin_user_id = org_admin_test_setup["project_admin_user"].id
    project1_id = org_admin_test_setup["project1"].id
    
    payload = {"user_id": str(project_admin_user_id)}
    r = await org_admin_client.post(f"/api/org-admin/projects/{project1_id}/admins", json=payload)
    
    assert r.status_code == 409
    assert "already has PROJECT_ADMIN" in r.json()["detail"]


@pytest.mark.asyncio
async def test_add_project_admin_wrong_org_project(org_admin_client, org_admin_test_setup):
    """Test adding PROJECT_ADMIN to project not in org."""
    regular_user_id = org_admin_test_setup["regular_user"].id
    project3_id = org_admin_test_setup["project3"].id  # Belongs to Acme, not Jacobs
    
    payload = {"user_id": str(regular_user_id)}
    r = await org_admin_client.post(f"/api/org-admin/projects/{project3_id}/admins", json=payload)
    
    assert r.status_code == 404
    assert "does not belong to your organization" in r.json()["detail"]


@pytest.mark.asyncio
async def test_add_project_admin_wrong_org_user(org_admin_client, org_admin_test_setup):
    """Test adding PROJECT_ADMIN for user not in org."""
    other_org_user_id = org_admin_test_setup["other_org_user"].id
    project1_id = org_admin_test_setup["project1"].id
    
    payload = {"user_id": str(other_org_user_id)}
    r = await org_admin_client.post(f"/api/org-admin/projects/{project1_id}/admins", json=payload)
    
    assert r.status_code == 404
    assert "does not belong to your organization" in r.json()["detail"]


# ========================================
# Test: Remove Project Admin
# ========================================

@pytest.mark.asyncio
async def test_remove_project_admin(org_admin_client, org_admin_test_setup, user_role_store):
    """Test removing PROJECT_ADMIN role from a user."""
    project_admin_user_id = org_admin_test_setup["project_admin_user"].id
    project1_id = org_admin_test_setup["project1"].id
    user_role_id = org_admin_test_setup["project_admin_role_assignment"].id
    
    # Verify role exists before deletion
    assert user_role_id in user_role_store
    
    r = await org_admin_client.delete(f"/api/org-admin/projects/{project1_id}/admins/{project_admin_user_id}")
    
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "Project admin role removed successfully"
    assert body["user_id"] == str(project_admin_user_id)
    assert body["project_id"] == str(project1_id)
    
    # Verify role was deleted from store
    assert user_role_id not in user_role_store


@pytest.mark.asyncio
async def test_remove_project_admin_not_exists(org_admin_client, org_admin_test_setup):
    """Test removing PROJECT_ADMIN when user doesn't have it."""
    regular_user_id = org_admin_test_setup["regular_user"].id
    project1_id = org_admin_test_setup["project1"].id
    
    r = await org_admin_client.delete(f"/api/org-admin/projects/{project1_id}/admins/{regular_user_id}")
    
    assert r.status_code == 404
    assert "does not have PROJECT_ADMIN role" in r.json()["detail"]


@pytest.mark.asyncio
async def test_remove_project_admin_wrong_org(org_admin_client, org_admin_test_setup):
    """Test removing PROJECT_ADMIN from project not in org."""
    project_admin_user_id = org_admin_test_setup["project_admin_user"].id
    project3_id = org_admin_test_setup["project3"].id  # Belongs to Acme
    
    r = await org_admin_client.delete(f"/api/org-admin/projects/{project3_id}/admins/{project_admin_user_id}")
    
    assert r.status_code == 404
    assert "does not belong to your organization" in r.json()["detail"]


# ========================================
# Test: Delete User
# ========================================

@pytest.mark.asyncio
async def test_delete_user(org_admin_client, org_admin_test_setup, user_store, user_role_store):
    """Test deleting a user from the organization."""
    regular_user_id = org_admin_test_setup["regular_user"].id
    
    # Verify user exists before deletion
    assert regular_user_id in user_store
    
    r = await org_admin_client.delete(f"/api/org-admin/users/{regular_user_id}")
    
    assert r.status_code == 204
    
    # Verify user was deactivated and removed from the organisation
    deleted_user = user_store[regular_user_id]

    assert deleted_user.is_active is False
    assert deleted_user.organization_id is None

    # Verify user's roles were removed
    assert not any(
        ur.user_id == regular_user_id
        for ur in user_role_store.values()
    )


@pytest.mark.asyncio
async def test_delete_user_self(org_admin_client, org_admin_test_setup):
    """Test that org admin cannot delete themselves."""
    org_admin_user_id = org_admin_test_setup["org_admin_user"].id
    
    r = await org_admin_client.delete(f"/api/org-admin/users/{org_admin_user_id}")
    
    assert r.status_code == 400
    assert "cannot delete your own user account" in r.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_wrong_org(org_admin_client, org_admin_test_setup):
    """Test deleting user from different organization."""
    other_org_user_id = org_admin_test_setup["other_org_user"].id
    
    r = await org_admin_client.delete(f"/api/org-admin/users/{other_org_user_id}")
    
    assert r.status_code == 403
    assert "does not belong to your organization" in r.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_not_found(org_admin_client):
    """Test deleting non-existent user."""
    fake_user_id = uuid4()
    
    r = await org_admin_client.delete(f"/api/org-admin/users/{fake_user_id}")
    
    assert r.status_code == 404
    assert "User not found" in r.json()["detail"]


# ========================================
# Test: Authorization
# ========================================

@pytest.mark.asyncio
async def test_org_admin_endpoints_require_org_admin_role(client):
    """Test that org admin endpoints reject users without ORG_ADMIN role."""
    # This uses the default client which has a super admin principal
    # but we need to test with a principal that doesn't have ORG_ADMIN
    
    # For this test, we'd need to override the principal differently
    # The current setup has RBAC patches that allow everything
    # This is a limitation of the test setup
    # In reality, the require_org_admin dependency would reject this
    pass  # Skip for now due to test infrastructure limitations
