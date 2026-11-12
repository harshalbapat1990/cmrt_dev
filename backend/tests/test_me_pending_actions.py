from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest


class _Mappings:
    def __init__(self, rows=()):
        self.rows = rows

    def all(self):
        return self.rows


class _Result:
    def __init__(self, rows=()):
        self.rows = rows

    def mappings(self):
        return _Mappings(self.rows)


class _Session:
    def __init__(self, results=()):
        self.queries = []
        self.results = list(results)

    async def execute(self, query):
        self.queries.append(query)
        return _Result(self.results.pop(0) if self.results else ())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("roles", "organisation_id", "expected_fragment", "unexpected_fragment"),
    [
        ({"PROJECT_ADMIN"}, None, "project_id IN (SELECT user_roles.scope_id", "project.proponent_org_id"),
        ({"ORG_ADMIN"}, uuid4(), "project.proponent_org_id =", "user_roles.scope_id"),
    ],
)
async def test_pending_actions_scope_both_sources_for_admin_roles(
    monkeypatch, roles, organisation_id, expected_fragment, unexpected_fragment
):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return roles if organisation_id is None else set()

    async def org_roles(_db, _user_id, _organisation_id):
        return roles

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    monkeypatch.setattr(me_router, "get_org_scoped_role_names", org_roles)

    session = _Session()
    await me_router.get_pending_actions(
        principal=SimpleNamespace(user_id=uuid4(), organization_id=organisation_id),
        db=session,
    )

    assert len(session.queries) == 2
    for query in session.queries:
        sql = str(query)
        assert expected_fragment in sql
        assert unexpected_fragment not in sql
    assert "user_roles.is_active = true" in str(session.queries[0]) if "PROJECT_ADMIN" in roles else True
    assert "project_reporting_submission.status IN" in str(session.queries[1])
    assert "project_stage_instances.stage IN" in str(session.queries[1])


@pytest.mark.asyncio
async def test_super_admin_pending_actions_include_period_identity_and_keep_option_actions(monkeypatch):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return {"SUPER_ADMIN"}

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    project_id, stage_id, period_id = uuid4(), uuid4(), uuid4()
    option_row = {
        "project_id": project_id,
        "project_name": "Project",
        "stage_instance_id": stage_id,
        "stage": "DESIGN",
        "report_number": 2,
        "num_reports_required": 2,
        "approval_status": "submitted",
    }
    period_row = {
        "project_id": project_id,
        "project_name": "Project",
        "stage_instance_id": stage_id,
        "stage": "RECURRING",
        "num_reports_required": 1,
        "approval_status": "awaiting_approval",
        "period_id": period_id,
        "period_label": "Mar 2027",
    }
    session = _Session([[option_row], [period_row]])

    results = await me_router.get_pending_actions(
        principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
        db=session,
    )

    assert len(results) == 2
    assert results[0].workflow_source == "project_option"
    assert results[0].report_number == 2
    assert results[1].workflow_source == "reporting_period"
    assert results[1].period_id == period_id
    assert results[1].period_label == "Mar 2027"
    assert results[1].approval_status == "awaiting_approval"
    assert "proponent_org_id" not in str(session.queries[0])
    assert "user_roles.scope_id" not in str(session.queries[0])




@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "stage"),
    [("awaiting_approval", "CONSTRUCTION"), ("reopen_requested", "RECURRING")],
)
async def test_pending_period_statuses_are_returned_once_with_distinct_period_ids(
    monkeypatch, status, stage
):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return {"SUPER_ADMIN"}

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    period_rows = [
        {
            "project_id": uuid4(),
            "project_name": "Period project",
            "stage_instance_id": uuid4(),
            "stage": stage,
            "num_reports_required": 1,
            "approval_status": status,
            "period_id": uuid4(),
            "period_label": label,
        }
        for label in ("Mar 2027", "Apr 2027")
    ]
    session = _Session([[], period_rows])

    actions = await me_router.get_pending_actions(
        principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
        db=session,
    )

    assert [action.approval_status for action in actions] == [status, status]
    assert [action.period_label for action in actions] == ["Mar 2027", "Apr 2027"]
    assert len({action.period_id for action in actions}) == 2
    assert all(action.workflow_source == "reporting_period" for action in actions)


@pytest.mark.asyncio
async def test_non_admin_pending_actions_are_limited_to_projects_with_admin_roles(monkeypatch):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return {"PROJECT_VIEWER"}

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    session = _Session()

    actions = await me_router.get_pending_actions(
        principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
        db=session,
    )

    assert actions == []
    assert len(session.queries) == 2
    assert all("project_id IN (SELECT user_roles.scope_id" in str(query) for query in session.queries)
