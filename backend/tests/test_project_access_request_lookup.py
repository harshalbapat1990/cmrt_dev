from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import access_requests as access_request_router
from routers import project as project_router
from schemas.access_requests import AccessRequestCreate


class QueryResult:
    def __init__(self, row=None):
        self.row = row

    def one_or_none(self):
        return self.row

    def scalars(self):
        return self

    def first(self):
        return self.row


class RecordingSession:
    def __init__(self, results=()):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self.results.pop(0) if self.results else QueryResult()

    async def commit(self):
        pass

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_lookup_finds_active_project_scoped_to_organisation_without_membership():
    project_id = uuid4()
    organisation_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_name="Test Proj",
        project_class="RECURRING",
    )
    db = RecordingSession([QueryResult(project)])

    result = await project_router.lookup_project_for_access_request(
        organisation_id=organisation_id,
        project_name="  test proj  ",
        _principal=SimpleNamespace(user_id=uuid4()),
        db=db,
    )

    assert result == {
        "id": project_id,
        "project_name": "Test Proj",
        "project_class": "RECURRING",
    }
    sql = str(db.statements[0]).lower()
    assert "project.proponent_org_id" in sql
    assert "project.is_active is true" in sql
    assert "lower(trim(project.project_name))" in sql
    assert "project.description" not in sql


@pytest.mark.asyncio
async def test_lookup_returns_none_when_project_does_not_match_organisation_or_name():
    db = RecordingSession([QueryResult()])

    result = await project_router.lookup_project_for_access_request(
        organisation_id=uuid4(),
        project_name="missing project",
        _principal=SimpleNamespace(user_id=uuid4()),
        db=db,
    )

    assert result is None


@pytest.mark.asyncio
async def test_project_access_request_rejects_mismatched_scope_before_creating(monkeypatch):
    created = False

    async def create(*args, **kwargs):
        nonlocal created
        created = True

    monkeypatch.setattr(access_request_router, "create_access_request", create)
    payload = AccessRequestCreate(
        request_type="PROJECT_EDITOR",
        scope_type="PROJECT",
        scope_id=uuid4(),
        project_id=uuid4(),
    )

    with pytest.raises(HTTPException) as error:
        await access_request_router.create_request(
            payload=payload,
            principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
            db=RecordingSession(),
        )

    assert error.value.status_code == 422
    assert not created


@pytest.mark.asyncio
async def test_project_access_request_rejects_wrong_organisation(monkeypatch):
    project_id = uuid4()
    actual_organisation_id = uuid4()
    db = RecordingSession([
        QueryResult(SimpleNamespace(proponent_org_id=actual_organisation_id))
    ])
    created = False

    async def create(*args, **kwargs):
        nonlocal created
        created = True

    monkeypatch.setattr(access_request_router, "create_access_request", create)
    payload = AccessRequestCreate(
        request_type="PROJECT_VIEWER",
        scope_type="PROJECT",
        scope_id=project_id,
        project_id=project_id,
        organisation_id=uuid4(),
    )

    with pytest.raises(HTTPException) as error:
        await access_request_router.create_request(
            payload=payload,
            principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
            db=db,
        )

    assert error.value.status_code == 422
    assert not created


@pytest.mark.asyncio
async def test_valid_project_access_request_keeps_project_and_organisation_scope(monkeypatch):
    project_id = uuid4()
    organisation_id = uuid4()
    project = SimpleNamespace(proponent_org_id=organisation_id)
    db = RecordingSession([QueryResult(project)])
    created_payload = None

    async def create(_db, payload, *, requester_user_id):
        nonlocal created_payload
        created_payload = payload
        return SimpleNamespace(
            id=uuid4(),
            request_type=payload.request_type,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            organisation_id=payload.organisation_id,
            project_id=payload.project_id,
            requested_role_id=uuid4(),
            target_user_id=requester_user_id,
        )

    monkeypatch.setattr(access_request_router, "create_access_request", create)
    monkeypatch.setattr(access_request_router, "write_audit_event", _noop)
    payload = AccessRequestCreate(
        request_type="project_editor",
        scope_type="project",
        scope_id=project_id,
        project_id=project_id,
        organisation_id=organisation_id,
    )

    result = await access_request_router.create_request(
        payload=payload,
        principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
        db=db,
    )

    assert result.project_id == project_id
    assert result.organisation_id == organisation_id
    assert created_payload.request_type == "PROJECT_EDITOR"
    assert created_payload.scope_type == "PROJECT"


async def _noop(*args, **kwargs):
    pass
