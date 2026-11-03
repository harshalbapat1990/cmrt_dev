"""Tests for /api/background-grade-metrics endpoints."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest


async def _setup_prerequisites(client):
    """Create a dataset revision and metric type needed for background grade metric records."""
    dr_resp = await client.post(
        "/api/dataset-revisions",
        json={"name": "Test Revision BGM"},
    )
    dataset_revision_id = dr_resp.json()["id"]

    mt_resp = await client.post(
        "/api/metric-types",
        json={"code": "material_share_capex_test", "name": "Material Share (Capex) Test"},
    )
    metric_type_id = mt_resp.json()["id"]

    gd_resp = await client.post("/api/grade-definitions", json={"id": 1, "name": "Grade 1"})
    grade_id = gd_resp.json()["id"]

    return dataset_revision_id, metric_type_id, grade_id


@pytest.mark.asyncio
async def test_list_background_grade_metrics_empty(client):
    dataset_revision_id, _, _ = await _setup_prerequisites(client)
    resp = await client.get(f"/api/background-grade-metrics?dataset_revision_id={dataset_revision_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_background_grade_metrics_requires_revision_context(client):
    response = await client.get("/api/background-grade-metrics?grade_id=3&limit=1")

    assert response.status_code == 400
    assert "dataset_revision_id is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_background_grade_metric(client):
    dataset_revision_id, metric_type_id, grade_id = await _setup_prerequisites(client)
    payload = {
        "dataset_revision_id": dataset_revision_id,
        "grade_id": grade_id,
        "metric_type_id": metric_type_id,
        "super_sector": "Roads",
        "mastertype": "New Construction",
        "value": "1.23",
    }
    resp = await client.post("/api/background-grade-metrics", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["grade_id"] == grade_id
    assert data["dataset_revision_id"] == dataset_revision_id


@pytest.mark.asyncio
async def test_get_background_grade_metric_by_id(client):
    dataset_revision_id, metric_type_id, grade_id = await _setup_prerequisites(client)
    payload = {
        "dataset_revision_id": dataset_revision_id,
        "grade_id": grade_id,
        "metric_type_id": metric_type_id,
    }
    create_resp = await client.post("/api/background-grade-metrics", json=payload)
    mid = create_resp.json()["id"]
    resp = await client.get(f"/api/background-grade-metrics/{mid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mid


@pytest.mark.asyncio
async def test_get_background_grade_metric_not_found(client):
    resp = await client.get(f"/api/background-grade-metrics/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_background_grade_metrics_filter_by_grade(client):
    dataset_revision_id, metric_type_id, grade_id = await _setup_prerequisites(client)
    payload = {"dataset_revision_id": dataset_revision_id, "grade_id": grade_id, "metric_type_id": metric_type_id}
    await client.post("/api/background-grade-metrics", json=payload)
    resp = await client.get(
        f"/api/background-grade-metrics?grade_id={grade_id}&dataset_revision_id={dataset_revision_id}"
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert all(r["grade_id"] == grade_id for r in results)


@pytest.mark.asyncio
async def test_patch_background_grade_metric(client):
    dataset_revision_id, metric_type_id, grade_id = await _setup_prerequisites(client)
    payload = {"dataset_revision_id": dataset_revision_id, "grade_id": grade_id, "metric_type_id": metric_type_id}
    create_resp = await client.post("/api/background-grade-metrics", json=payload)
    mid = create_resp.json()["id"]
    resp = await client.patch(f"/api/background-grade-metrics/{mid}", json={"value": "9.99"})
    assert resp.status_code == 200
    assert resp.json()["value"] == "9.99"


@pytest.mark.asyncio
async def test_superseding_metric_deactivates_old_row_and_creates_active_replacement():
    """Editing a metric preserves history while making only the replacement current."""
    from crud.background_grade_metrics import supersede_background_grade_metric
    from models.background_grade_metrics import BackgroundGradeMetric

    old = BackgroundGradeMetric(
        id=uuid4(),
        dataset_revision_id=uuid4(),
        grade_id=3,
        metric_type_id=uuid4(),
        value="1.4",
        is_active=True,
    )

    class Session:
        def __init__(self):
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            pass

        async def refresh(self, _obj):
            pass

    db = Session()
    replacement = await supersede_background_grade_metric(db, old, {"value": "2.4"})

    assert old.is_active is False
    assert replacement.is_active is True
    assert replacement.value == "2.4"
    assert replacement.dataset_revision_id == old.dataset_revision_id
    assert db.added == [old, replacement]


@pytest.mark.asyncio
async def test_natural_key_lookup_is_revision_scoped_and_excludes_inactive_rows():
    from crud.background_grade_metrics import (
        _BGM_NATURAL_KEY_FIELDS,
        get_background_grade_metric_by_natural_key,
    )

    revision_id = uuid4()
    metric_id = uuid4()
    natural_key = {
        field: (
            3 if field == "grade_id"
            else str(uuid4()) if field in {
                "jurisdiction_id", "mastertype_id", "typecast_id",
                "emissions_category_id", "emissions_subcategory_id",
                "metric_type_id", "unit_id",
            }
            else None
        )
        for field in _BGM_NATURAL_KEY_FIELDS
    }
    active_metric = SimpleNamespace(id=metric_id, is_active=True)

    class Scalars:
        def all(self):
            return [active_metric]

    class Result:
        def scalars(self):
            return Scalars()

    class Session:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return Result()

    db = Session()
    found = await get_background_grade_metric_by_natural_key(db, revision_id, natural_key)

    assert found is active_metric
    sql = str(db.statement).lower()
    assert "background_grade_metrics.is_active is true" in sql
    assert "background_grade_metrics.dataset_revision_id" in sql


@pytest.mark.asyncio
async def test_patch_background_grade_metric_not_found(client):
    resp = await client.patch(f"/api/background-grade-metrics/{uuid4()}", json={"value": "1.0"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_background_grade_metric(client):
    dataset_revision_id, metric_type_id, grade_id = await _setup_prerequisites(client)
    payload = {"dataset_revision_id": dataset_revision_id, "grade_id": grade_id, "metric_type_id": metric_type_id}
    create_resp = await client.post("/api/background-grade-metrics", json=payload)
    mid = create_resp.json()["id"]
    assert (await client.delete(f"/api/background-grade-metrics/{mid}")).status_code == 204
    assert (await client.get(f"/api/background-grade-metrics/{mid}")).status_code == 404
    listed = await client.get(
        f"/api/background-grade-metrics?dataset_revision_id={dataset_revision_id}"
    )
    assert listed.status_code == 200
    assert all(row["id"] != mid for row in listed.json())


@pytest.mark.asyncio
async def test_delete_background_grade_metric_not_found(client):
    resp = await client.delete(f"/api/background-grade-metrics/{uuid4()}")
    assert resp.status_code == 404
