from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest


class _Mappings:
    def all(self):
        return []


class _Result:
    def mappings(self):
        return _Mappings()


class _Session:
    def __init__(self):
        self.query = None

    async def execute(self, query):
        self.query = query
        return _Result()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("roles", "organisation_id", "expected_fragment", "unexpected_fragment"),
    [
        ({"PROJECT_ADMIN"}, None, "project_id IN (SELECT user_roles.scope_id", "project.proponent_org_id"),
        ({"ORG_ADMIN"}, uuid4(), "project.proponent_org_id =", "user_roles.scope_id"),
    ],
)
async def test_pending_actions_are_scoped_for_the_admin_roles(
    monkeypatch,
    roles,
    organisation_id,
    expected_fragment,
    unexpected_fragment,
):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return roles if organisation_id is None else set()

    async def org_roles(_db, _user_id, _organisation_id):
        return roles

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    monkeypatch.setattr(me_router, "get_org_scoped_role_names", org_roles)

    principal = SimpleNamespace(user_id=uuid4(), organization_id=organisation_id)
    session = _Session()
    await me_router.get_pending_actions(principal=principal, db=session)

    sql = str(session.query)
    assert expected_fragment in sql
    assert unexpected_fragment not in sql
    if "PROJECT_ADMIN" in roles:
        assert "user_roles.is_active = true" in sql


@pytest.mark.asyncio
async def test_super_admin_pending_actions_are_platform_wide(monkeypatch):
    import routers.me as me_router

    async def effective_roles(_db, _user_id):
        return {"SUPER_ADMIN"}

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)

    session = _Session()
    await me_router.get_pending_actions(
        principal=SimpleNamespace(user_id=uuid4(), organization_id=None),
        db=session,
    )

    sql = str(session.query)
    assert "project_options.approval_status IN" in sql
    assert "proponent_org_id" not in sql
    assert "user_roles.scope_id" not in sql
