from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.parametrize("scope_type", ["ORG", "PROJECT"])
@pytest.mark.asyncio
async def test_org_or_project_revision_can_be_unpublished_after_confirming_current_bindings(
    client, dataset_revision_store, project_dataset_revision_store, scope_type,
):
    from tests.conftest import DummyDatasetRevision, DummyProjectDatasetRevision

    revision_id = uuid4()
    project_id = uuid4()
    dataset_revision_store[revision_id] = DummyDatasetRevision(
        id=revision_id,
        name="Org dataset",
        status="published",
        scope_type=scope_type,
        scope_id=project_id if scope_type == "PROJECT" else uuid4(),
    )
    project_dataset_revision_store[uuid4()] = DummyProjectDatasetRevision(
        id=uuid4(), project_id=project_id, dataset_revision_id=revision_id
    )

    preview = await client.get(f"/api/dataset-revisions/{revision_id}/bindings")
    assert preview.status_code == 200
    assert preview.json()["projects"] == [
        {"project_id": str(project_id), "project_name": f"Project {project_id}"}
    ]

    stale_confirmation = await client.post(
        f"/api/dataset-revisions/{revision_id}/unpublish",
        json={"confirm_bound_project_ids": []},
    )
    assert stale_confirmation.status_code == 409
    assert stale_confirmation.json()["detail"]["code"] == "bindings_changed"
    assert dataset_revision_store[revision_id].status == "published"

    confirmed = await client.post(
        f"/api/dataset-revisions/{revision_id}/unpublish",
        json={"confirm_bound_project_ids": [str(project_id)]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_deprecation_is_blocked_for_any_bound_project(client, dataset_revision_store, project_dataset_revision_store):
    from tests.conftest import DummyDatasetRevision, DummyProjectDatasetRevision

    revision_id = uuid4()
    project_id = uuid4()
    dataset_revision_store[revision_id] = DummyDatasetRevision(
        id=revision_id, name="Bound revision", status="published", scope_type="PROJECT", scope_id=project_id
    )
    project_dataset_revision_store[uuid4()] = DummyProjectDatasetRevision(
        id=uuid4(), project_id=project_id, dataset_revision_id=revision_id
    )

    blocked = await client.post(f"/api/dataset-revisions/{revision_id}/deprecate")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "revision_bound"
    assert dataset_revision_store[revision_id].status == "published"

    project_dataset_revision_store.clear()
    preview = await client.get(f"/api/dataset-revisions/{revision_id}/bindings")
    assert preview.status_code == 200
    assert preview.json()["projects"] == []
    project_dataset_revision_store[uuid4()] = DummyProjectDatasetRevision(
        id=uuid4(), project_id=project_id, dataset_revision_id=revision_id
    )
    raced = await client.post(f"/api/dataset-revisions/{revision_id}/deprecate")
    assert raced.status_code == 409
    assert raced.json()["detail"]["code"] == "revision_bound"

    project_dataset_revision_store.clear()
    allowed = await client.post(f"/api/dataset-revisions/{revision_id}/deprecate")
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_republish_recalculates_bound_projects_and_reports_partial_failures(
    client, dataset_revision_store, project_dataset_revision_store, emissions_factor_set_store, monkeypatch
):
    import services.project_dataset_recalculation as recalculation_service
    from services.project_dataset_recalculation import ProjectDatasetRecalculationError
    from tests.conftest import DummyDatasetRevision, DummyEmissionsFactorSet, DummyProjectDatasetRevision

    revision_id = uuid4()
    project_ok = uuid4()
    project_failed = uuid4()
    dataset_revision_store[revision_id] = DummyDatasetRevision(
        id=revision_id, name="Revised org dataset", status="draft", scope_type="ORG", scope_id=uuid4()
    )
    for project_id in (project_ok, project_failed):
        project_dataset_revision_store[uuid4()] = DummyProjectDatasetRevision(
            id=uuid4(), project_id=project_id, dataset_revision_id=revision_id
        )
    factor_set_id = uuid4()
    emissions_factor_set_store[factor_set_id] = DummyEmissionsFactorSet(
        id=factor_set_id, name="Factors", version="1", dataset_revision_id=revision_id
    )
    recalculated = []

    async def recalculate(_db, project_id, _revision_id):
        recalculated.append(project_id)
        if project_id == project_failed:
            raise ProjectDatasetRecalculationError({
                "missing_data": [],
                "calculation_errors": [{"entry": "Road users", "message": "Factor lookup failed"}],
                "recalculated_count": 2,
            })
        return {
            "missing_data": [{"entry": "Drainage", "dataset_table": "Grade 2 factors"}],
            "calculation_errors": [],
            "recalculated_count": 4,
        }

    monkeypatch.setattr(recalculation_service, "recalculate_project_for_revision", recalculate)

    response = await client.post(f"/api/dataset-revisions/{revision_id}/publish")
    assert response.status_code == 200, response.text
    assert dataset_revision_store[revision_id].status == "published"
    assert set(recalculated) == {project_ok, project_failed}

    reports = {item["project_id"]: item for item in response.json()["project_recalculations"]}
    assert reports[str(project_ok)]["status"] == "recalculated"
    assert reports[str(project_ok)]["recalculated_count"] == 4
    assert reports[str(project_ok)]["missing_data"][0]["dataset_table"] == "Grade 2 factors"
    assert reports[str(project_failed)]["status"] == "failed"
    assert reports[str(project_failed)]["calculation_errors"][0]["message"] == "Factor lookup failed"
