"""Tests for /api/background-grade-metrics endpoints."""
from __future__ import annotations

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
    resp = await client.get("/api/background-grade-metrics")
    assert resp.status_code == 200
    assert resp.json() == []


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
    resp = await client.get(f"/api/background-grade-metrics?grade_id={grade_id}")
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


@pytest.mark.asyncio
async def test_delete_background_grade_metric_not_found(client):
    resp = await client.delete(f"/api/background-grade-metrics/{uuid4()}")
    assert resp.status_code == 404
