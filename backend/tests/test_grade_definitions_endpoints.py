"""Tests for /api/grade-definitions endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_list_grade_definitions_empty(client):
    resp = await client.get("/api/grade-definitions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_grade_definition(client):
    resp = await client.post("/api/grade-definitions", json={"id": 1, "name": "Grade 1"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Grade 1"


@pytest.mark.asyncio
async def test_create_grade_definition_conflict(client):
    await client.post("/api/grade-definitions", json={"id": 2, "name": "Grade 2"})
    resp = await client.post("/api/grade-definitions", json={"id": 2, "name": "Grade 2 Dup"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_grade_definition_by_id(client):
    await client.post("/api/grade-definitions", json={"id": 3, "name": "Grade 3"})
    resp = await client.get("/api/grade-definitions/3")
    assert resp.status_code == 200
    assert resp.json()["id"] == 3


@pytest.mark.asyncio
async def test_get_grade_definition_not_found(client):
    resp = await client.get("/api/grade-definitions/99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_grade_definition(client):
    await client.post("/api/grade-definitions", json={"id": 4, "name": "Grade 4"})
    resp = await client.patch("/api/grade-definitions/4", json={"name": "Grade 4 Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Grade 4 Updated"


@pytest.mark.asyncio
async def test_patch_grade_definition_not_found(client):
    resp = await client.patch("/api/grade-definitions/99", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_grade_definition(client):
    await client.post("/api/grade-definitions", json={"id": 5, "name": "Grade 5"})
    resp = await client.delete("/api/grade-definitions/5")
    assert resp.status_code == 204
    assert (await client.get("/api/grade-definitions/5")).status_code == 404


@pytest.mark.asyncio
async def test_delete_grade_definition_not_found(client):
    resp = await client.delete("/api/grade-definitions/99")
    assert resp.status_code == 404
