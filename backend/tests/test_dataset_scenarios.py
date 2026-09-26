#TC1  : publish empty revision → 422
#TC2  : unpublish with bound project → 409
#TC3  : deprecate published revision → 200, status=deprecated
#TC4  : archive with bound project → 409
#TC5a : publish archived revision → 409 (archived is terminal)
#TC5b : unpublish archived revision → 409
#TC5c : deprecate archived revision → 409
#TC5d : archived revision cannot be re-archived → 409
#TC6  : bind project → draft revision → 409
#TC7  : bind project → published revision → 201
#TC8  : bind project → deprecated revision → 409
#TC9  : bind project → archived revision → 409
#TC10 : exclusion list empty initially → []
#TC11 : create exclusion → stored, excluded_from_revision=True
#TC12 : list exclusions by project returns only that project's rows
#TC13 : delete exclusion → 204, no longer listed
#TC14 : migrate binding to non-published revision → 409
#TC15 : factor set lock makes PATCH forbidden → 409
#TC16 : locked factor set cannot be deleted → 409
#TC17 : duplicate (clone) factor set creates new unlocked copy
#TC18 : GET transport distances returns 200 (defaults endpoint exists)
#TC19 : GET waste rates returns 200 (defaults endpoint exists)
#TC20 : GET densities returns 200 (defaults endpoint exists)
#BRANCH : branch creates new draft; original status unchanged

from __future__ import annotations

from uuid import uuid4

import pytest

REV_NAME = "Scenarios Rev"
PROJ_ID = str(uuid4())


async def _create_revision(client, name=REV_NAME, **extra):
    payload = {"name": name, **extra}
    resp = await client.post("/api/dataset-revisions", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _add_factor_set(client, revision_id, *, name="FS", version="1.0"):
    payload: dict = {"name": name, "version": version}
    if revision_id is not None:
        payload["dataset_revision_id"] = str(revision_id)
    resp = await client.post("/api/emissions-factor-sets", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _publish(client, revision_id):
    resp = await client.post(f"/api/dataset-revisions/{revision_id}/publish")
    return resp


async def _bind(client, project_id, revision_id):
    resp = await client.post(
        "/api/project-dataset-revisions",
        json={"project_id": project_id, "dataset_revision_id": revision_id},
    )
    return resp


@pytest.mark.asyncio
async def test_tc1_publish_empty_revision_fails(client):
    rev = await _create_revision(client, name="TC1 Rev")
    resp = await _publish(client, rev["id"])
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_tc2_unpublish_with_bound_project_fails(client):
    rev = await _create_revision(client, name="TC2 Rev")
    await _add_factor_set(client, rev["id"], name="TC2 FS")
    pub = await _publish(client, rev["id"])
    assert pub.status_code == 200

    bind = await _bind(client, str(uuid4()), rev["id"])
    assert bind.status_code == 201

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/unpublish")
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc3_deprecate_always_succeeds(client):
    rev = await _create_revision(client, name="TC3 Rev")
    await _add_factor_set(client, rev["id"], name="TC3 FS")
    await _publish(client, rev["id"])

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/deprecate")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_tc4_archive_with_bound_project_fails(client):
    rev = await _create_revision(client, name="TC4 Rev")
    await _add_factor_set(client, rev["id"], name="TC4 FS")
    await _publish(client, rev["id"])
    await _bind(client, str(uuid4()), rev["id"])

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/archive")
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc5a_archived_cannot_be_published(client):
    rev = await _create_revision(client, name="TC5a Rev")
    await client.post(f"/api/dataset-revisions/{rev['id']}/archive")

    resp = await _publish(client, rev["id"])
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc5b_archived_cannot_be_unpublished(client):
    rev = await _create_revision(client, name="TC5b Rev")
    await client.post(f"/api/dataset-revisions/{rev['id']}/archive")

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/unpublish")
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc5c_archived_cannot_be_deprecated(client):
    rev = await _create_revision(client, name="TC5c Rev")
    await client.post(f"/api/dataset-revisions/{rev['id']}/archive")

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/deprecate")
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc5d_archived_cannot_be_archived_again(client):
    rev = await _create_revision(client, name="TC5d Rev")
    first = await client.post(f"/api/dataset-revisions/{rev['id']}/archive")
    assert first.status_code == 200

    second = await client.post(f"/api/dataset-revisions/{rev['id']}/archive")
    assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_tc5_deprecated_can_be_archived(client):
    rev = await _create_revision(client, name="TC5 Dep Arc")
    await _add_factor_set(client, rev["id"], name="TC5 FS")
    await _publish(client, rev["id"])
    await client.post(f"/api/dataset-revisions/{rev['id']}/deprecate")

    resp = await client.post(f"/api/dataset-revisions/{rev['id']}/archive")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_tc6_bind_to_draft_fails(client):
    rev = await _create_revision(client, name="TC6 Rev")
    assert rev["status"] == "draft"

    resp = await _bind(client, str(uuid4()), rev["id"])
    assert resp.status_code == 409, resp.text
    assert "published" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_tc7_bind_to_published_succeeds(client):
    rev = await _create_revision(client, name="TC7 Rev")
    await _add_factor_set(client, rev["id"], name="TC7 FS")
    await _publish(client, rev["id"])

    resp = await _bind(client, str(uuid4()), rev["id"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["dataset_revision_id"] == rev["id"]


@pytest.mark.asyncio
async def test_tc8_bind_to_deprecated_fails(client):
    rev = await _create_revision(client, name="TC8 Rev")
    await _add_factor_set(client, rev["id"], name="TC8 FS")
    await _publish(client, rev["id"])
    await client.post(f"/api/dataset-revisions/{rev['id']}/deprecate")

    resp = await _bind(client, str(uuid4()), rev["id"])
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc9_bind_to_archived_fails(client):
    rev = await _create_revision(client, name="TC9 Rev")
    await client.post(f"/api/dataset-revisions/{rev['id']}/archive")

    resp = await _bind(client, str(uuid4()), rev["id"])
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc14_migrate_to_non_published_fails(client):
    rev = await _create_revision(client, name="TC14 Rev")
    resp = await client.post(
        "/api/project-dataset-revisions/migrate",
        json={"project_id": str(uuid4()), "to_revision_id": rev["id"]},
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_tc10_exclusions_empty_by_default(client):
    project_id = str(uuid4())
    resp = await client.get(f"/api/project-dataset-exclusions/by-project/{project_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_tc11_create_exclusion_stores_row(client):
    project_id = str(uuid4())
    metric_id = str(uuid4())
    payload = {
        "project_id": project_id,
        "metric_id": metric_id,
        "excluded_from_revision": True,
        "reason": "project-specific value",
    }
    resp = await client.post("/api/project-dataset-exclusions", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["metric_id"] == metric_id
    assert data["excluded_from_revision"] is True


@pytest.mark.asyncio
async def test_tc12_list_exclusions_scoped_to_project(client):
    project_a = str(uuid4())
    project_b = str(uuid4())

    for pid in (project_a, project_b):
        await client.post(
            "/api/project-dataset-exclusions",
            json={"project_id": pid, "metric_id": str(uuid4()), "excluded_from_revision": True},
        )

    resp = await client.get(f"/api/project-dataset-exclusions/by-project/{project_a}")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["project_id"] == project_a


@pytest.mark.asyncio
async def test_tc13_delete_exclusion(client):
    project_id = str(uuid4())
    create_resp = await client.post(
        "/api/project-dataset-exclusions",
        json={"project_id": project_id, "metric_id": str(uuid4()), "excluded_from_revision": True},
    )
    exc_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/project-dataset-exclusions/{exc_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/project-dataset-exclusions/by-project/{project_id}")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_tc15_locked_factor_set_cannot_be_patched(client):
    fs_id = await _add_factor_set(client, None, name="TC15 FS Lock", version="lock-1")
    lock_resp = await client.post(f"/api/emissions-factor-sets/{fs_id}/lock")
    assert lock_resp.status_code == 200
    assert lock_resp.json()["is_locked"] is True

    patch_resp = await client.patch(
        f"/api/emissions-factor-sets/{fs_id}", json={"notes": "should fail"}
    )
    assert patch_resp.status_code == 409, patch_resp.text


@pytest.mark.asyncio
async def test_tc16_locked_factor_set_cannot_be_deleted(client):
    fs_id = await _add_factor_set(client, None, name="TC16 FS Del", version="del-1")
    await client.post(f"/api/emissions-factor-sets/{fs_id}/lock")

    del_resp = await client.delete(f"/api/emissions-factor-sets/{fs_id}")
    assert del_resp.status_code == 409, del_resp.text


@pytest.mark.asyncio
async def test_tc17_duplicate_factor_set_is_unlocked(client):
    fs_id = await _add_factor_set(client, None, name="TC17 FS Dup", version="src-1")
    await client.post(f"/api/emissions-factor-sets/{fs_id}/lock")

    dup_resp = await client.post(
        f"/api/emissions-factor-sets/{fs_id}/duplicate",
        json={"new_version": "clone-1"},
    )
    assert dup_resp.status_code == 201, dup_resp.text
    clone = dup_resp.json()
    assert clone["is_locked"] is False
    assert clone["id"] != fs_id


@pytest.mark.asyncio
async def test_tc18_default_transport_distances_endpoint_exists(client):
    revision = await _create_revision(client, name="TC18 transport read")
    resp = await client.get(
        f"/api/default-transport-distances?dataset_revision_id={revision['id']}"
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_tc19_default_waste_rates_endpoint_exists(client):
    revision = await _create_revision(client, name="TC19 waste read")
    resp = await client.get(
        f"/api/default-waste-rates?dataset_revision_id={revision['id']}"
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_tc20_densities_endpoint_exists(client):
    revision = await _create_revision(client, name="TC20 densities read")
    resp = await client.get(f"/api/densities?dataset_revision_id={revision['id']}")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_branch_creates_draft_and_preserves_source(client):
    rev = await _create_revision(client, name="Branch Source")
    await _add_factor_set(client, rev["id"], name="Branch FS")
    await _publish(client, rev["id"])

    branch_resp = await client.post(
        f"/api/dataset-revisions/{rev['id']}/branch",
        json={"name": "Branch Fork"},
    )
    assert branch_resp.status_code == 201, branch_resp.text
    branch = branch_resp.json()
    assert branch["status"] == "draft"
    assert branch["id"] != rev["id"]
    assert branch["name"] == "Branch Fork"

    orig = await client.get(f"/api/dataset-revisions/{rev['id']}")
    assert orig.json()["status"] == "published"


@pytest.mark.asyncio
async def test_branch_name_conflict_fails(client):
    rev = await _create_revision(client, name="BranchConflict Source")

    resp = await client.post(
        f"/api/dataset-revisions/{rev['id']}/branch",
        json={"name": "BranchConflict Source"},
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_branch_nonexistent_revision_fails(client):
    resp = await client.post(
        f"/api/dataset-revisions/{uuid4()}/branch",
        json={"name": "Ghost Branch"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_publish_then_unpublish_restores_draft(client):
    rev = await _create_revision(client, name="Repub Rev")
    await _add_factor_set(client, rev["id"], name="Repub FS")
    await _publish(client, rev["id"])

    unp = await client.post(f"/api/dataset-revisions/{rev['id']}/unpublish")
    assert unp.status_code == 200, unp.text
    assert unp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_draft_archive_is_terminal(client):
    rev = await _create_revision(client, name="Draft Arc Rev")
    arc = await client.post(f"/api/dataset-revisions/{rev['id']}/archive")
    assert arc.status_code == 200, arc.text
    assert arc.json()["status"] == "archived"

    assert (await client.post(f"/api/dataset-revisions/{rev['id']}/publish")).status_code == 409


@pytest.mark.asyncio
async def test_filter_revisions_by_status(client):
    rev1 = await _create_revision(client, name="Filter Draft Rev")
    rev2 = await _create_revision(client, name="Filter Published Rev")
    await _add_factor_set(client, rev2["id"], name="Filter FS")
    await _publish(client, rev2["id"])

    resp = await client.get("/api/dataset-revisions?status=draft")
    assert resp.status_code == 200
    statuses = [r["status"] for r in resp.json()]
    assert all(s == "draft" for s in statuses), statuses

    resp2 = await client.get("/api/dataset-revisions?status=published")
    assert resp2.status_code == 200
    statuses2 = [r["status"] for r in resp2.json()]
    assert all(s == "published" for s in statuses2), statuses2


@pytest.mark.asyncio
async def test_cannot_publish_from_deprecated(client):
    rev = await _create_revision(client, name="Dep Pub Rev")
    await _add_factor_set(client, rev["id"], name="Dep Pub FS")
    await _publish(client, rev["id"])
    await client.post(f"/api/dataset-revisions/{rev['id']}/deprecate")

    resp = await _publish(client, rev["id"])
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_archived_revision_cannot_be_edited(client):
    rev = await _create_revision(client, name="Arc Edit Rev")
    await client.post(f"/api/dataset-revisions/{rev['id']}/archive")

    resp = await client.patch(f"/api/dataset-revisions/{rev['id']}", json={"notes": "attempt"})
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_delete_revision_blocked_when_bound(client):
    rev = await _create_revision(client, name="Del Bound Rev")
    await _add_factor_set(client, rev["id"], name="Del Bound FS")
    await _publish(client, rev["id"])
    await _bind(client, str(uuid4()), rev["id"])

    resp = await client.delete(f"/api/dataset-revisions/{rev['id']}")
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_delete_revision_blocked_when_has_factor_sets(client):
    rev = await _create_revision(client, name="Del FS Rev")
    await _add_factor_set(client, rev["id"], name="Del FS Item")

    resp = await client.delete(f"/api/dataset-revisions/{rev['id']}")
    assert resp.status_code == 409, resp.text
