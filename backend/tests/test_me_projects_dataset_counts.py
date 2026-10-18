from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_my_projects_include_counts_for_only_accessible_project_revisions(client, app, monkeypatch):
    import routers.me as me_router
    from schemas.project import ProjectOut

    accessible_id = uuid4()
    second_accessible_id = uuid4()
    inaccessible_id = uuid4()
    projects = [
        ProjectOut(
            id=accessible_id,
            project_name="Bridge renewal",
            project_type_id=uuid4(),
            project_class="SMALL",
            proponent_org_id=uuid4(),
            created_by_user_id=uuid4(),
        ),
        ProjectOut(
            id=second_accessible_id,
            project_name="Road upgrade",
            project_type_id=uuid4(),
            project_class="SMALL",
            proponent_org_id=uuid4(),
            created_by_user_id=uuid4(),
        ),
    ]

    async def effective_roles(_db, _user_id):
        return []

    async def visible_projects(_db, _user_id):
        return projects

    monkeypatch.setattr(me_router, "get_effective_role_names", effective_roles)
    monkeypatch.setattr(me_router, "list_projects_for_user_roles", visible_projects)

    from core.session import get_session

    captured_queries = []

    class CountResult:
        def all(self):
            return [
                SimpleNamespace(project_id=accessible_id, status="draft", count=1),
                SimpleNamespace(project_id=accessible_id, status="deprecated", count=2),
                SimpleNamespace(project_id=second_accessible_id, status="published", count=3),
                # An inaccessible project must not appear in the scoped aggregation.
                SimpleNamespace(project_id=inaccessible_id, status="archived", count=9),
            ]

    class CountSession:
        async def execute(self, query):
            captured_queries.append(query)
            return CountResult()

    async def override_session():
        yield CountSession()

    previous_override = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = override_session
    try:
        response = await client.get("/api/me/projects")
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous_override

    assert response.status_code == 200
    payload = {project["id"]: project for project in response.json()}
    assert payload[str(accessible_id)]["dataset_revision_counts"] == {
        "draft": 1,
        "published": 0,
        "deprecated": 2,
        "archived": 0,
    }
    assert payload[str(second_accessible_id)]["dataset_revision_counts"] == {
        "draft": 0,
        "published": 3,
        "deprecated": 0,
        "archived": 0,
    }
    assert len(captured_queries) == 1

    where_clause = str(captured_queries[0])
    assert "dataset_revisions.scope_type =" in where_clause
    assert "dataset_revisions.scope_id IN" in where_clause

