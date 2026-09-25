"""
test_identity_endpoints.py
==========================
Tests for the public registration endpoint (POST /api/identity/register).

Business rules under test:
  - Duplicate email → 409
  - Scenario A (existing org): missing org → 404
  - Scenario A: domain mismatch → 400
  - Scenario A: domain match, proponent org → 201 with pending OA request
  - Scenario A: domain match, non-proponent org → 201 without OA request
  - Scenario B (new org): missing org_name / org_type → 422
  - Scenario B1: valid proponent org → 201 with pending OA request
  - Scenario B2: valid non-proponent org → 201 without OA request
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from conftest import DummyUser, DummyOrganization


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_local_jwt_mode(monkeypatch: pytest.MonkeyPatch):
    """Force local_jwt auth mode so tests can supply email directly in the payload."""
    import core.config as cfg
    monkeypatch.setattr(cfg.settings, "auth_mode", "local_jwt")


@pytest.fixture(autouse=True)
def patch_identity_crud(monkeypatch: pytest.MonkeyPatch):
    """Patch all CRUD/domain helpers imported into the identity router."""
    import routers.identity as id_router

    _dummy_org = DummyOrganization(
        id=uuid4(),
        name="Test Org",
        organization_type="DESIGNERS",
        is_active=True,
        created_on=datetime.utcnow(),
    )

    _dummy_user = DummyUser(
        id=uuid4(),
        email="newuser@nsw.gov.au",
        first_name="Jane",
        last_name="Doe",
        is_active=True,
        organization_id=_dummy_org.id,
        created_on=datetime.utcnow(),
    )

    class _DummyAR:
        def __init__(self):
            self.id = uuid4()
            self.request_type = "ORG_ADMIN"
            self.status = "PENDING"
            self.scope_type = "ORGANISATION"

    class _DummyRole:
        def __init__(self):
            self.id = uuid4()
            self.name = "GENERAL_USER"

    class _DummyUserRole:
        def __init__(self):
            self.id = uuid4()

    # Default stubs (can be overridden per-test via additional monkeypatches)
    async def _no_existing_user(_db, email):
        return None

    async def _get_org_found(_db, org_id):
        return _dummy_org

    async def _domain_match(_db, org_id, email):
        return True

    async def _create_user(_db, payload):
        return _dummy_user

    async def _add_domain(_db, org_id, domain):
        return None

    async def _create_ar(_db, payload, *, requester_user_id):
        return _DummyAR()

    async def _get_role_by_name(_db, name):
        return _DummyRole()

    async def _create_user_role(_db, user_id, role_id, scope_type=None, scope_id=None, is_active=True):
        return _DummyUserRole()

    monkeypatch.setattr(id_router, "get_user_by_email", _no_existing_user)
    monkeypatch.setattr(id_router, "get_organization", _get_org_found)
    monkeypatch.setattr(id_router, "domain_matches_org", _domain_match)
    monkeypatch.setattr(id_router, "create_user", _create_user)
    monkeypatch.setattr(id_router, "add_domain", _add_domain)
    monkeypatch.setattr(id_router, "create_access_request", _create_ar)
    monkeypatch.setattr(id_router, "get_role_by_name", _get_role_by_name)
    monkeypatch.setattr(id_router, "create_user_role", _create_user_role)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client, monkeypatch):
    """If the email is already registered, return 409 Conflict."""
    import routers.identity as id_router

    _existing = DummyUser(id=uuid4(), email="dup@example.com")

    async def _dup_user(_db, email):
        return _existing

    monkeypatch.setattr(id_router, "get_user_by_email", _dup_user)

    payload = {
        "email": "dup@example.com",
        "first_name": "Dup",
        "last_name": "User",
        "org_name": "New Org",
        "org_type": "DESIGNERS",
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


@pytest.mark.asyncio
async def test_register_scenario_a_org_not_found_returns_404(client, monkeypatch):
    """Joining an existing org that doesn't exist → 404."""
    import routers.identity as id_router

    async def _no_org(_db, org_id):
        return None

    monkeypatch.setattr(id_router, "get_organization", _no_org)

    org_id = str(uuid4())
    payload = {
        "email": "user@nsw.gov.au",
        "first_name": "Jane",
        "last_name": "Doe",
        "organisation_id": org_id,
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_scenario_a_domain_mismatch_returns_400(client, monkeypatch):
    """Email domain doesn't match org's allowed domains → 400."""
    import routers.identity as id_router

    async def _no_match(_db, org_id, email):
        return False

    monkeypatch.setattr(id_router, "domain_matches_org", _no_match)

    org_id = str(uuid4())
    payload = {
        "email": "jane@gmail.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "organisation_id": org_id,
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 400
    assert "domain" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_scenario_a_domain_match_returns_201(client):
    """Valid Scenario A with proponent org: domain matches → user + pending OA request created."""
    org_id = str(uuid4())
    payload = {
        "email": "jane@nsw.gov.au",
        "first_name": "Jane",
        "last_name": "Doe",
        "organisation_id": org_id,
        "org_admin_reason": "I manage road projects for TfNSW",
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert "user_id" in body
    assert "org_admin_request_id" in body
    assert body["org_admin_request_id"] is not None
    assert body["org_created"] is False


@pytest.mark.asyncio
async def test_register_scenario_a_non_proponent_org_no_oa_request(client, monkeypatch):
    """Valid Scenario A with non-proponent org: user registered, no OA request submitted."""
    import routers.identity as id_router

    _non_proponent_org = DummyOrganization(
        id=uuid4(),
        name="Supporting Org",
        organization_type="CONTRACTORS",
        is_active=True,
        is_proponent=False,
        created_on=datetime.utcnow(),
    )

    async def _get_non_proponent_org(_db, org_id):
        return _non_proponent_org

    monkeypatch.setattr(id_router, "get_organization", _get_non_proponent_org)

    payload = {
        "email": "contractor@contractor.com",
        "first_name": "Bob",
        "last_name": "Builder",
        "organisation_id": str(_non_proponent_org.id),
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert "user_id" in body
    assert body["org_admin_request_id"] is None
    assert "general member" in body["message"].lower()


@pytest.mark.asyncio
async def test_register_scenario_b_missing_org_fields_returns_422(client):
    """New org registration without org_name / org_type → 422."""
    payload = {
        "email": "founder@neworg.com",
        "first_name": "Alice",
        "last_name": "Smith",
        # No organisation_id, no org_name/org_type
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_scenario_b_proponent_org_returns_201(client):
    """Valid Scenario B1: proponent org bootstrap → 201 with org_created=True and pending OA request."""
    payload = {
        "email": "founder@brandneworg.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "org_name": "Brand New Proponent Org",
        "org_type": "DESIGNERS",
        "is_proponent": True,
        "org_admin_reason": "Setting up for my road authority",
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert "user_id" in body
    assert body["org_created"] is True
    assert body["org_admin_request_id"] is not None
    assert "pending" in body["message"].lower()


@pytest.mark.asyncio
async def test_register_scenario_b_non_proponent_org_no_oa_request(client):
    """Valid Scenario B2: non-proponent org bootstrap → 201 with org_created=True but NO OA request."""
    payload = {
        "email": "contractor@newcontractor.com",
        "first_name": "Charlie",
        "last_name": "Contractor",
        "org_name": "Roads Contractor Pty Ltd",
        "org_type": "CONTRACTORS",
        "is_proponent": False,
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert "user_id" in body
    assert body["org_created"] is True
    assert body["org_admin_request_id"] is None
    assert "general member" in body["message"].lower()


@pytest.mark.asyncio
async def test_register_assigns_general_user_role_proponent(client, monkeypatch):
    """GENERAL_USER role is auto-assigned at ORGANISATION scope for proponent registrations."""
    import routers.identity as id_router

    calls: list[dict] = []

    async def _tracking_create_user_role(_db, user_id, role_id, scope_type=None, scope_id=None, is_active=True):
        calls.append({"scope_type": scope_type, "is_active": is_active})
        class _R:
            id = uuid4()
        return _R()

    monkeypatch.setattr(id_router, "create_user_role", _tracking_create_user_role)

    payload = {
        "email": "jane@nsw.gov.au",
        "first_name": "Jane",
        "last_name": "Doe",
        "organisation_id": str(uuid4()),
        "org_admin_reason": "I manage road projects",
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    assert len(calls) == 1
    assert calls[0]["scope_type"] == "ORGANISATION"
    assert calls[0]["is_active"] is True


@pytest.mark.asyncio
async def test_register_assigns_general_user_role_non_proponent(client, monkeypatch):
    """GENERAL_USER is auto-assigned even for non-proponent org registrations."""
    import routers.identity as id_router

    _non_proponent_org = DummyOrganization(
        id=uuid4(),
        name="Contractor Co",
        organization_type="CONTRACTORS",
        is_active=True,
        is_proponent=False,
        created_on=datetime.utcnow(),
    )

    async def _get_non_proponent(_db, org_id):
        return _non_proponent_org

    monkeypatch.setattr(id_router, "get_organization", _get_non_proponent)

    calls: list[dict] = []

    async def _tracking_create_user_role(_db, user_id, role_id, scope_type=None, scope_id=None, is_active=True):
        calls.append({"scope_type": scope_type, "is_active": is_active})
        class _R:
            id = uuid4()
        return _R()

    monkeypatch.setattr(id_router, "create_user_role", _tracking_create_user_role)

    payload = {
        "email": "contractor@contractor.com",
        "first_name": "Bob",
        "last_name": "Builder",
        "organisation_id": str(_non_proponent_org.id),
        "accepted_pics": True,
        "accepted_terms": True,
    }
    r = await client.post("/api/identity/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["org_admin_request_id"] is None
    assert len(calls) == 1
    assert calls[0]["scope_type"] == "ORGANISATION"
