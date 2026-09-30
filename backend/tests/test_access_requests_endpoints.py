"""
test_access_requests_endpoints.py
===================================
Tests for the access-request lifecycle endpoints
(POST / GET / approve / reject / cancel).
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4, UUID
from dataclasses import dataclass, field
from typing import Optional

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest


# ---------------------------------------------------------------------------
# Dummy access-request object
# ---------------------------------------------------------------------------

@dataclass
class DummyAR:
    id: UUID = field(default_factory=uuid4)
    request_type: str = "ORG_ADMIN"
    status: str = "PENDING"
    requester_user_id: Optional[UUID] = None
    target_user_id: Optional[UUID] = None
    requested_role_id: Optional[UUID] = None
    scope_type: str = "ORGANISATION"
    scope_id: Optional[UUID] = None
    organisation_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    reason: Optional[str] = None
    decision_note: Optional[str] = None
    reviewed_by_user_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    created_on: datetime = field(default_factory=datetime.utcnow)
    updated_on: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Shared fixture: patch access-request CRUD in router namespace
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_ar_crud(monkeypatch: pytest.MonkeyPatch):
    import routers.access_requests as ar_router

    _store: dict[UUID, DummyAR] = {}

    async def _create(db, payload, *, requester_user_id):
        ar = DummyAR(
            id=uuid4(),
            request_type=payload.request_type,
            requester_user_id=requester_user_id,
            target_user_id=getattr(payload, "target_user_id", None),
            requested_role_id=getattr(payload, "requested_role_id", None),
            scope_type=payload.scope_type,
            scope_id=getattr(payload, "scope_id", None),
            organisation_id=getattr(payload, "organisation_id", None),
            project_id=getattr(payload, "project_id", None),
            reason=getattr(payload, "reason", None),
        )
        _store[ar.id] = ar
        return ar

    async def _list(db, status_filter=None, request_type=None, organisation_id=None,
                    project_id=None, project_ids=None, target_user_id=None, skip=0, limit=50):
        items = list(_store.values())
        if status_filter:
            items = [a for a in items if a.status == status_filter]
        if project_ids is not None:
            items = [a for a in items if a.project_id in project_ids]
        if target_user_id:
            items = [a for a in items if a.target_user_id == target_user_id]
        return items[skip:skip + limit]

    _list_enriched = _list

    async def _get(db, request_id):
        return _store.get(request_id)

    async def _approve(db, request_id, reviewer_id, note):
        ar = _store[request_id]
        ar.status = "APPROVED"
        ar.reviewed_by_user_id = reviewer_id
        ar.decision_note = note
        return ar

    async def _reject(db, request_id, reviewer_id, note):
        ar = _store[request_id]
        ar.status = "REJECTED"
        ar.reviewed_by_user_id = reviewer_id
        ar.decision_note = note
        return ar

    async def _cancel(db, request_id, *, requester_user_id):
        ar = _store[request_id]
        ar.status = "CANCELLED"
        return ar

    async def _create_user_role(db, *, user_id, role_id, scope_type, scope_id, is_active):
        pass  # no-op in tests

    monkeypatch.setattr(ar_router, "create_access_request", _create)
    monkeypatch.setattr(ar_router, "list_access_requests", _list)
    monkeypatch.setattr(ar_router, "list_access_requests_enriched", _list_enriched)
    monkeypatch.setattr(ar_router, "get_access_request", _get)
    monkeypatch.setattr(ar_router, "approve_access_request", _approve)
    monkeypatch.setattr(ar_router, "reject_access_request", _reject)
    monkeypatch.setattr(ar_router, "cancel_access_request", _cancel)
    monkeypatch.setattr(ar_router, "create_user_role", _create_user_role)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_access_request(client):
    """POST /api/access-requests → 201 with PENDING status."""
    payload = {
        "request_type": "ORG_ADMIN",
        "scope_type": "ORGANISATION",
        "scope_id": str(uuid4()),
        "organisation_id": str(uuid4()),
        "reason": "I manage road programs for this org",
    }
    r = await client.post("/api/access-requests", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["request_type"] == "ORG_ADMIN"
    assert body["status"] == "PENDING"
    assert "id" in body


@pytest.mark.asyncio
async def test_super_admin_request_must_be_self_service(client):
    r = await client.post("/api/access-requests", json={
        "request_type": "SUPER_ADMIN",
        "target_user_id": str(uuid4()),
        "scope_type": "GLOBAL",
        "scope_id": None,
        "reason": "Need global access",
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_request_requires_reason(client):
    r = await client.post("/api/access-requests", json={
        "request_type": "SUPER_ADMIN",
        "scope_type": "GLOBAL",
        "scope_id": None,
        "reason": "   ",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_current_user_super_admin_request_status_is_self_scoped(client):
    r = await client.get("/api/access-requests/mine/super-admin")
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.asyncio
async def test_list_access_requests_empty(client):
    """GET /api/access-requests → 200 empty list when no requests exist."""
    r = await client.get("/api/access-requests")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_access_requests_returns_created(client):
    """After submitting a request, it must appear in the list."""
    org_id = str(uuid4())
    await client.post(
        "/api/access-requests",
        json={
            "request_type": "ORG_ADMIN",
            "scope_type": "ORGANISATION",
            "scope_id": org_id,
            "organisation_id": org_id,
        },
    )
    r = await client.get("/api/access-requests")
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_get_access_request_not_found(client):
    """GET /api/access-requests/{id} for non-existent id → 404."""
    r = await client.get(f"/api/access-requests/{uuid4()}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_access_request_found(client):
    """GET /api/access-requests/{id} for existing request → 200."""
    org_id = str(uuid4())
    create_r = await client.post(
        "/api/access-requests",
        json={"request_type": "ORG_ADMIN", "scope_type": "ORGANISATION",
              "scope_id": org_id, "organisation_id": org_id},
    )
    ar_id = create_r.json()["id"]

    r = await client.get(f"/api/access-requests/{ar_id}")
    assert r.status_code == 200
    assert r.json()["id"] == ar_id


@pytest.mark.asyncio
async def test_approve_access_request(client):
    """POST /api/access-requests/{id}/approve → 200 APPROVED status."""
    org_id = str(uuid4())
    create_r = await client.post(
        "/api/access-requests",
        json={"request_type": "ORG_ADMIN", "scope_type": "ORGANISATION",
              "scope_id": org_id, "organisation_id": org_id},
    )
    ar_id = create_r.json()["id"]

    r = await client.post(f"/api/access-requests/{ar_id}/approve",
                          json={"decision_note": "Looks good"})
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_reject_access_request(client):
    """POST /api/access-requests/{id}/reject → 200 REJECTED status."""
    org_id = str(uuid4())
    create_r = await client.post(
        "/api/access-requests",
        json={"request_type": "ORG_ADMIN", "scope_type": "ORGANISATION",
              "scope_id": org_id, "organisation_id": org_id},
    )
    ar_id = create_r.json()["id"]

    r = await client.post(f"/api/access-requests/{ar_id}/reject",
                          json={"decision_note": "Not approved at this time"})
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_cancel_access_request(client):
    """POST /api/access-requests/{id}/cancel → 200 CANCELLED status."""
    org_id = str(uuid4())
    create_r = await client.post(
        "/api/access-requests",
        json={"request_type": "ORG_ADMIN", "scope_type": "ORGANISATION",
              "scope_id": org_id, "organisation_id": org_id},
    )
    ar_id = create_r.json()["id"]

    r = await client.post(f"/api/access-requests/{ar_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_approve_non_existent_request_returns_404(client):
    """Approving a non-existent request → 404."""
    r = await client.post(f"/api/access-requests/{uuid4()}/approve")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_by_status(client):
    """Status filter query param should narrow results."""
    org_id = str(uuid4())
    create_r = await client.post(
        "/api/access-requests",
        json={"request_type": "ORG_ADMIN", "scope_type": "ORGANISATION",
              "scope_id": org_id, "organisation_id": org_id},
    )
    ar_id = create_r.json()["id"]
    await client.post(f"/api/access-requests/{ar_id}/approve")

    # PENDING list should be empty now
    r = await client.get("/api/access-requests?status=PENDING")
    assert r.status_code == 200
    pending = r.json()
    assert all(a["status"] == "PENDING" for a in pending)


# ---------------------------------------------------------------------------
# Broadcast visibility tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_admin_sees_requests_for_their_project(client, monkeypatch):
    """PROJECT_ADMIN can list PENDING requests for projects they administer."""
    import routers.access_requests as ar_router
    from core.rbac import PROJECT_ADMIN

    project_id = uuid4()

    async def _pa_roles(_db, user_id, project_id=None):
        return [PROJECT_ADMIN]

    async def _admin_projects(_db, user_id):
        return [project_id]

    monkeypatch.setattr(ar_router, "get_effective_role_names", _pa_roles)
    monkeypatch.setattr(ar_router, "get_project_ids_where_admin", _admin_projects)

    r = await client.post("/api/access-requests", json={
        "request_type": "PROJECT_EDITOR",
        "scope_type": "PROJECT",
        "scope_id": str(project_id),
        "project_id": str(project_id),
        "organisation_id": str(uuid4()),
        "reason": "I want to contribute to this project",
    })
    assert r.status_code == 201
    ar_id = r.json()["id"]

    r = await client.get("/api/access-requests")
    assert r.status_code == 200
    assert ar_id in [a["id"] for a in r.json()]


@pytest.mark.asyncio
async def test_project_admin_excluded_from_other_project_requests(client, monkeypatch):
    """Requests for a project the user does NOT admin are excluded."""
    import routers.access_requests as ar_router
    from core.rbac import PROJECT_ADMIN

    other_project_id = uuid4()
    my_project_id = uuid4()

    async def _pa_roles(_db, user_id, project_id=None):
        return [PROJECT_ADMIN]

    async def _admin_projects(_db, user_id):
        return [my_project_id]  # NOT other_project_id

    monkeypatch.setattr(ar_router, "get_effective_role_names", _pa_roles)
    monkeypatch.setattr(ar_router, "get_project_ids_where_admin", _admin_projects)

    r = await client.post("/api/access-requests", json={
        "request_type": "PROJECT_VIEWER",
        "scope_type": "PROJECT",
        "scope_id": str(other_project_id),
        "project_id": str(other_project_id),
        "organisation_id": str(uuid4()),
    })
    assert r.status_code == 201
    ar_id = r.json()["id"]

    r = await client.get("/api/access-requests")
    assert r.status_code == 200
    assert ar_id not in [a["id"] for a in r.json()]


@pytest.mark.asyncio
async def test_project_admin_can_view_specific_request_for_their_project(client, monkeypatch):
    """PROJECT_ADMIN may GET a specific pending request for their project."""
    import routers.access_requests as ar_router
    from core.rbac import PROJECT_ADMIN

    project_id = uuid4()

    # Create under default (SUPER_ADMIN) context
    r = await client.post("/api/access-requests", json={
        "request_type": "PROJECT_EDITOR",
        "scope_type": "PROJECT",
        "scope_id": str(project_id),
        "project_id": str(project_id),
        "organisation_id": str(uuid4()),
    })
    assert r.status_code == 201
    ar_id = r.json()["id"]

    # Now switch to PROJECT_ADMIN context
    async def _pa_roles(_db, user_id, project_id=None):
        return [PROJECT_ADMIN]

    monkeypatch.setattr(ar_router, "get_effective_role_names", _pa_roles)

    r = await client.get(f"/api/access-requests/{ar_id}")
    assert r.status_code == 200
    assert r.json()["id"] == ar_id


@pytest.mark.asyncio
async def test_first_approval_wins_second_returns_409(client, monkeypatch):
    """Once a request is approved, a second approve attempt returns 409."""
    import routers.access_requests as ar_router

    _store2: dict[UUID, DummyAR] = {}

    async def _create2(db, payload, *, requester_user_id):
        ar = DummyAR(
            id=uuid4(),
            request_type=payload.request_type,
            status="PENDING",
            requester_user_id=requester_user_id,
            target_user_id=getattr(payload, "target_user_id", None) or requester_user_id,
            scope_type=payload.scope_type,
            scope_id=getattr(payload, "scope_id", None),
            organisation_id=getattr(payload, "organisation_id", None),
        )
        _store2[ar.id] = ar
        return ar

    async def _get2(db, request_id):
        return _store2.get(request_id)

    async def _approve2(db, request_id, reviewer_id, note):
        from fastapi import HTTPException as _HTTPEx
        ar = _store2.get(request_id)
        if ar is None:
            raise _HTTPEx(status_code=404, detail="Not found")
        if ar.status != "PENDING":
            raise _HTTPEx(status_code=409, detail=f"Request is already {ar.status}")
        ar.status = "APPROVED"
        ar.reviewed_by_user_id = reviewer_id
        ar.decision_note = note
        return ar

    monkeypatch.setattr(ar_router, "create_access_request", _create2)
    monkeypatch.setattr(ar_router, "get_access_request", _get2)
    monkeypatch.setattr(ar_router, "approve_access_request", _approve2)

    org_id = str(uuid4())
    r = await client.post("/api/access-requests", json={
        "request_type": "ORG_ADMIN",
        "scope_type": "ORGANISATION",
        "scope_id": org_id,
        "organisation_id": org_id,
    })
    assert r.status_code == 201
    ar_id = r.json()["id"]

    # First admin approves → succeeds
    r = await client.post(f"/api/access-requests/{ar_id}/approve", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    # Second admin tries to approve → 409 (already closed)
    r = await client.post(f"/api/access-requests/{ar_id}/approve", json={})
    assert r.status_code == 409
