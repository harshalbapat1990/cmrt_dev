"""
test_rbac_enforcement.py
========================
Tests for the RBAC evaluation engine (core/rbac.py) and role-enforcement
at the API boundary.

Unit tests here do NOT hit a real DB; they monkeypatch
``get_effective_role_names`` and inspect that the HTTP layer enforces the
correct boundaries.

Tests cover:
  - Separation of duties: SUPER_ADMIN can only grant SUPER_ADMIN or ORG_ADMIN
  - Separation of duties: ORG_ADMIN can only grant PROJECT_ADMIN
  - Separation of duties: PROJECT_ADMIN can only grant PROJECT_EDITOR or PROJECT_VIEWER
  - require_role dependency rejects callers below the required role
  - require_role dependency accepts callers with an exact or higher role
  - scope type validation rejects unknown scope types
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from core.rbac import (
    SUPER_ADMIN, ORG_ADMIN, PROJECT_ADMIN, PROJECT_EDITOR, PROJECT_VIEWER,
    GLOBAL, ORGANISATION, PROJECT,
    _GRANT_CEILING,
    assert_can_grant_role,
    validate_scope,   # imported here so module binding is captured before autouse patches
)
from core.security import Principal


# ---------------------------------------------------------------------------
# Separation-of-duties unit tests (test _GRANT_CEILING constant directly)
# ---------------------------------------------------------------------------

class TestGrantCeilings:
    def test_super_admin_can_only_grant_super_admin_and_org_admin(self):
        ceiling = _GRANT_CEILING[SUPER_ADMIN]
        assert SUPER_ADMIN in ceiling
        assert ORG_ADMIN in ceiling
        assert PROJECT_ADMIN not in ceiling
        assert PROJECT_EDITOR not in ceiling
        assert PROJECT_VIEWER not in ceiling

    def test_org_admin_cannot_grant_super_admin(self):
        assert SUPER_ADMIN not in _GRANT_CEILING[ORG_ADMIN]

    def test_org_admin_cannot_grant_org_admin(self):
        assert ORG_ADMIN not in _GRANT_CEILING[ORG_ADMIN]

    def test_org_admin_can_grant_project_admin(self):
        """ORG_ADMIN can directly grant PROJECT_ADMIN only."""
        ceiling = _GRANT_CEILING[ORG_ADMIN]
        assert PROJECT_ADMIN in ceiling

    def test_org_admin_cannot_directly_grant_editor_or_viewer(self):
        """PROJECT_EDITOR and PROJECT_VIEWER are NOT in ORG_ADMIN's direct ceiling.
        They become available only when the caller also holds PROJECT_ADMIN on that project."""
        ceiling = _GRANT_CEILING[ORG_ADMIN]
        assert PROJECT_EDITOR not in ceiling
        assert PROJECT_VIEWER not in ceiling

    def test_project_admin_cannot_grant_org_admin(self):
        assert ORG_ADMIN not in _GRANT_CEILING[PROJECT_ADMIN]

    def test_project_admin_cannot_grant_super_admin(self):
        assert SUPER_ADMIN not in _GRANT_CEILING[PROJECT_ADMIN]

    def test_project_admin_can_grant_editor_and_viewer(self):
        ceiling = _GRANT_CEILING[PROJECT_ADMIN]
        assert PROJECT_EDITOR in ceiling
        assert PROJECT_VIEWER in ceiling


# ---------------------------------------------------------------------------
# assert_can_grant_role async unit tests
# ---------------------------------------------------------------------------

class TestAssertCanGrantRole:
    """Pure logic tests — db not needed since get_effective_role_names is patched."""

    @pytest.mark.asyncio
    async def test_super_admin_can_grant_org_admin(self, monkeypatch):
        import core.rbac as rbac

        async def _mock_roles(_db, user_id, project_id=None):
            return {SUPER_ADMIN}

        monkeypatch.setattr(rbac, "get_effective_role_names", _mock_roles)

        caller = Principal(user_id=uuid4(), email="sa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        # Should not raise
        await assert_can_grant_role(None, caller, ORG_ADMIN, ORGANISATION, uuid4())

    @pytest.mark.asyncio
    async def test_org_admin_cannot_grant_super_admin_raises(self, monkeypatch):
        import core.rbac as rbac
        from fastapi import HTTPException

        async def _mock_roles(_db, user_id, project_id=None):
            return {ORG_ADMIN}

        monkeypatch.setattr(rbac, "get_effective_role_names", _mock_roles)

        caller = Principal(user_id=uuid4(), email="oa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        with pytest.raises(HTTPException) as exc:
            await assert_can_grant_role(None, caller, SUPER_ADMIN, GLOBAL, None)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_project_admin_cannot_grant_org_admin_raises(self, monkeypatch):
        import core.rbac as rbac
        from fastapi import HTTPException

        # Must patch BOTH helpers – autouse stubs them with SUPER_ADMIN/ORG_ADMIN
        # which would allow the grant; override to simulate a PROJECT_ADMIN caller.
        async def _pa_only(_db, user_id, project_id=None):
            return {PROJECT_ADMIN}

        async def _pa_only_org(_db, user_id, organisation_id=None):
            return {PROJECT_ADMIN}

        monkeypatch.setattr(rbac, "get_effective_role_names", _pa_only)
        monkeypatch.setattr(rbac, "get_org_scoped_role_names", _pa_only_org)

        caller = Principal(user_id=uuid4(), email="pa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        with pytest.raises(HTTPException) as exc:
            await assert_can_grant_role(None, caller, ORG_ADMIN, ORGANISATION, uuid4())
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_role_cannot_grant_anything(self, monkeypatch):
        import core.rbac as rbac
        from fastapi import HTTPException

        async def _mock_roles(_db, user_id, project_id=None):
            return set()

        monkeypatch.setattr(rbac, "get_effective_role_names", _mock_roles)

        caller = Principal(user_id=uuid4(), email="nobody@test.com",
                           oidc_issuer="i", oidc_sub="s")
        with pytest.raises(HTTPException) as exc:
            await assert_can_grant_role(None, caller, PROJECT_VIEWER, PROJECT, uuid4())
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# require_role API enforcer tests (HTTP boundary)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_require_role_blocks_insufficient_role(client, monkeypatch):
    """
    A user with only PROJECT_VIEWER should be blocked from an endpoint
    that requires SUPER_ADMIN.  We simulate this by making the RBAC check
    return only PROJECT_VIEWER and then hitting an SA-only endpoint.
    """
    import core.rbac as rbac

    async def _viewer_only(_db, user_id, project_id=None):
        return {PROJECT_VIEWER}

    async def _org_viewer_only(_db, user_id, organisation_id=None):
        return {PROJECT_VIEWER}

    # Patch the core module – require_role closure references core.rbac directly.
    monkeypatch.setattr(rbac, "get_effective_role_names", _viewer_only)
    monkeypatch.setattr(rbac, "get_org_scoped_role_names", _org_viewer_only)

    # POST /api/organizations requires SUPER_ADMIN; use a valid org_type enum value
    r = await client.post(
        "/api/organizations",
        json={"name": "Blocked Org", "organization_type": "DESIGNERS"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_require_role_permits_super_admin(client, monkeypatch):
    """
    A user with SUPER_ADMIN must be able to reach SA-only endpoints.
    The conftest global patch already returns all roles, so this just verifies
    the fixture wires up correctly.
    """
    import routers.organization as org_router
    from uuid import uuid4
    from datetime import datetime
    from conftest import DummyOrganization

    async def _create_org_stub(_db, payload):
        return DummyOrganization(
            id=uuid4(),
            name=payload.name,
            organization_type="DESIGNERS",
            created_on=datetime.utcnow(),
        )

    monkeypatch.setattr(org_router, "create_organization", _create_org_stub)

    # Use a valid Organization_Type enum value (DESIGNERS | CONTRACTORS)
    r = await client.post(
        "/api/organizations",
        json={"name": "Allowed Org", "organization_type": "DESIGNERS"},
    )
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Scope validation unit tests
# ---------------------------------------------------------------------------

class TestValidateScope:
    """Tests for validate_scope() helper."""

    @pytest.mark.asyncio
    async def test_global_scope_with_null_scope_id_passes(self):
        # Use the module-level `validate_scope` reference (captured before autouse
        # patches, so it points to the real implementation – not the noop stub).
        caller = Principal(user_id=uuid4(), email="sa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        # GLOBAL scope with None scope_id should not raise
        await validate_scope(None, GLOBAL, None, caller=caller)

    @pytest.mark.asyncio
    async def test_invalid_scope_type_raises_422(self):
        from fastapi import HTTPException

        caller = Principal(user_id=uuid4(), email="sa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        with pytest.raises(HTTPException) as exc:
            await validate_scope(None, "MADE_UP_SCOPE", None, caller=caller)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_non_global_scope_without_scope_id_raises_422(self):
        from fastapi import HTTPException

        caller = Principal(user_id=uuid4(), email="sa@test.com",
                           oidc_issuer="i", oidc_sub="s")
        with pytest.raises(HTTPException) as exc:
            await validate_scope(None, ORGANISATION, None, caller=caller)
        assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Stage authorization policy tests
# ---------------------------------------------------------------------------

from core.authorization_policy import (
    AccessLevel,
    ROLE_ALLOWED_SCOPES,
    STAGE_ACCESS_MANAGERS,
    can_manage_stage_access,
    stage_access_for_role,
)


def test_super_admin_does_not_get_stage_access_from_role_alone():
    """
    SUPER_ADMIN is a platform administrator and does not automatically
    receive project/stage access.
    """
    assert stage_access_for_role(SUPER_ADMIN) == AccessLevel.NONE


def test_project_viewer_has_view_stage_access():
    assert stage_access_for_role(PROJECT_VIEWER) == AccessLevel.VIEW


def test_project_editor_has_edit_stage_access():
    assert stage_access_for_role(PROJECT_EDITOR) == AccessLevel.EDIT


def test_unknown_role_has_no_stage_access():
    assert stage_access_for_role("UNKNOWN_ROLE") == AccessLevel.NONE


def test_org_admin_can_manage_stage_access():
    assert can_manage_stage_access({ORG_ADMIN}) is True


def test_project_admin_cannot_manage_stage_access_yet():
    """
    Phase 1 deliberately gives stage-access administration to ORG_ADMIN only.
    This can later be changed centrally in STAGE_ACCESS_MANAGERS.
    """
    assert can_manage_stage_access({PROJECT_ADMIN}) is False


def test_super_admin_cannot_manage_stage_access_yet():
    """
    SUPER_ADMIN does not automatically receive project-access administration.
    """
    assert can_manage_stage_access({SUPER_ADMIN}) is False


def test_mixed_roles_include_stage_access_manager():
    assert can_manage_stage_access(
        {
            PROJECT_VIEWER,
            ORG_ADMIN,
        }
    ) is True


def test_role_scope_policy():
    assert ROLE_ALLOWED_SCOPES[PROJECT_EDITOR] == {"STAGE"}
    assert ROLE_ALLOWED_SCOPES[PROJECT_VIEWER] == {"STAGE"}

    assert ROLE_ALLOWED_SCOPES[PROJECT_ADMIN] == {"PROJECT"}
    assert ROLE_ALLOWED_SCOPES[ORG_ADMIN] == {"ORGANISATION"}

    assert ROLE_ALLOWED_SCOPES[SUPER_ADMIN] == {"GLOBAL"}