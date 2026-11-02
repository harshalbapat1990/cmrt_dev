"""
Tests for project stage-instance lifecycle.

These tests verify that ProjectStageInstance records are treated as
persistent business entities:

- Existing enabled stages keep their instance IDs.
- Newly enabled stages create new instances.
- Disabled stages remain in the database.
- Disabled stages lose ordinary stage access.
- Re-enabled stages reuse their original instance IDs.
- Configuration changes update the existing instance in place.
- Recurring projects keep a single RECURRING instance.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from crud.project import _sync_project_stage_instances
from models.project_stage_instances import (
    ProjectStageInstance,
    ProjectStage,
)
from models.project_stage_config import (
    ProjectStageConfig,
    ProjectStage as ConfigProjectStage,
    ReportFrequency,
)
from models.user_roles import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeScalars:
    def __init__(self, items=None):
        self._items = list(items or [])

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class FakeResult:
    def __init__(self, items=None):
        self._items = list(items or [])

    def scalars(self):
        return FakeScalars(self._items)

    def all(self):
        return list(self._items)


class FakeSession:
    """
    Minimal AsyncSession replacement for _sync_project_stage_instances().

    execute() responses are supplied in FIFO order because the helper makes
    three kinds of queries:

      1. Existing stage instances
      2. PROJECT_EDITOR / PROJECT_VIEWER role IDs
      3. Existing stage UserRole records when disabling a stage
    """

    def __init__(self, execute_returns=None):
        self._execute_queue = list(execute_returns or [])
        self.added = []

    async def execute(self, query):
        if self._execute_queue:
            result = self._execute_queue.pop(0)

            if isinstance(result, FakeResult):
                return result

            if isinstance(result, list):
                return FakeResult(result)

            return FakeResult([result])

        return FakeResult([])

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        # Mimic SQLAlchemy assigning IDs to newly inserted objects.
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()

    def added_of_type(self, model_type):
        return [
            obj
            for obj in self.added
            if isinstance(obj, model_type)
        ]


def make_project():
    return SimpleNamespace(id=uuid4())


def make_stage_instance(
    project_id,
    stage,
    *,
    sequence=1,
    num_reports_required=1,
    frequency="ANNUAL",
):
    return ProjectStageInstance(
        id=uuid4(),
        project_id=project_id,
        stage=stage,
        sequence=sequence,
        num_reports_required=num_reports_required,
        frequency=frequency,
        approval_status="draft",
    )


def make_stage_config(
    project_id,
    stage,
    *,
    enabled=True,
    num_reports_required=1,
    frequency="ANNUAL",
    min_requirements=None,
):
    return ProjectStageConfig(
        project_id=project_id,
        stage=stage,
        enabled=enabled,
        num_reports_required=num_reports_required,
        frequency=frequency,
        min_requirements=min_requirements,
    )


# ---------------------------------------------------------------------------
# 1. Existing enabled stage -> same instance ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_enabled_stage_preserves_instance_id():
    project = make_project()

    existing = make_stage_instance(
        project.id,
        ProjectStage.BUSINESS_CASE,
        sequence=1,
        num_reports_required=2,
        frequency="ANNUAL",
    )

    config = make_stage_config(
        project.id,
        ConfigProjectStage.BUSINESS_CASE,
        enabled=True,
        num_reports_required=2,
        frequency="ANNUAL",
    )

    original_id = existing.id

    db = FakeSession(
        execute_returns=[
            [existing],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    assert existing.id == original_id
    assert existing.project_id == project.id
    assert existing.stage == ProjectStage.BUSINESS_CASE

    # The existing ORM object may be re-added to the session.
    # Verify that no replacement/new instance was created.
    created = [
        obj
        for obj in db.added_of_type(ProjectStageInstance)
        if obj is not existing
    ]
    assert created == []


# ---------------------------------------------------------------------------
# 2. New enabled stage -> new instance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_enabled_stage_creates_new_instance():
    project = make_project()

    config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=True,
        num_reports_required=3,
        frequency="QUARTERLY",
    )

    db = FakeSession(
        execute_returns=[
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    created = [
        obj
        for obj in db.added_of_type(ProjectStageInstance)
        if obj.stage != ProjectStage.BUSINESS_CASE
    ]

    assert len(created) == 1

    instance = created[0]

    assert instance.project_id == project.id
    assert instance.stage == ProjectStage.DESIGN
    assert instance.sequence == 2
    assert instance.num_reports_required == 3
    assert instance.frequency == "QUARTERLY"
    assert instance.approval_status == "draft"


# ---------------------------------------------------------------------------
# 3. Disable existing stage -> instance remains
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_stage_instance_is_retained():
    project = make_project()

    existing = make_stage_instance(
        project.id,
        ProjectStage.DESIGN,
        sequence=2,
    )

    config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=False,
    )

    original_id = existing.id

    db = FakeSession(
        execute_returns=[
            [existing],
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    assert existing.id == original_id
    assert existing.project_id == project.id
    assert existing.stage == ProjectStage.DESIGN

    # The existing instance must not be deleted or replaced.
    assert existing not in db.added_of_type(ProjectStageInstance)


# ---------------------------------------------------------------------------
# 4. Disable existing stage -> ordinary assignments become inactive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabling_stage_deactivates_editor_and_viewer_assignments():
    project = make_project()

    existing = make_stage_instance(
        project.id,
        ProjectStage.DESIGN,
        sequence=2,
    )

    editor_role_id = uuid4()
    viewer_role_id = uuid4()

    editor_assignment = UserRole(
        user_id=uuid4(),
        role_id=editor_role_id,
        scope_type="STAGE",
        scope_id=existing.id,
        is_active=True,
    )

    viewer_assignment = UserRole(
        user_id=uuid4(),
        role_id=viewer_role_id,
        scope_type="STAGE",
        scope_id=existing.id,
        is_active=True,
    )

    config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=False,
    )

    db = FakeSession(
        execute_returns=[
            [existing],
            [editor_role_id, viewer_role_id],
            [editor_assignment, viewer_assignment],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    assert editor_assignment.is_active is False
    assert viewer_assignment.is_active is False

    # The stage itself still exists.
    assert existing.id is not None
    assert existing.stage == ProjectStage.DESIGN


# ---------------------------------------------------------------------------
# 5. Disable -> re-enable -> original instance ID reused
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reenabled_stage_reuses_original_instance_id():
    project = make_project()

    existing = make_stage_instance(
        project.id,
        ProjectStage.DESIGN,
        sequence=2,
        num_reports_required=2,
        frequency="ANNUAL",
    )

    original_id = existing.id

    # First operation: stage disabled.
    disabled_config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=False,
    )

    db_disable = FakeSession(
        execute_returns=[
            [existing],
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db_disable,
        project=project,
        stage_configs=[disabled_config],
    )

    assert existing.id == original_id

    # Second operation: same stage is enabled again.
    enabled_config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=True,
        num_reports_required=4,
        frequency="MONTHLY",
    )

    db_enable = FakeSession(
        execute_returns=[
            [existing],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db_enable,
        project=project,
        stage_configs=[enabled_config],
    )

    assert existing.id == original_id
    assert existing.num_reports_required == 4
    assert existing.frequency == "MONTHLY"

    # The existing ORM object may be re-added to the session.
    # Verify that no replacement/new instance was created.
    created = [
        obj
        for obj in db_enable.added_of_type(ProjectStageInstance)
        if obj is not existing
    ]
    assert created == []


# ---------------------------------------------------------------------------
# 6. Configuration change -> existing instance updated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_configuration_change_updates_existing_instance_without_replacing_it():
    project = make_project()

    existing = make_stage_instance(
        project.id,
        ProjectStage.CONSTRUCTION,
        sequence=3,
        num_reports_required=1,
        frequency="ANNUAL",
    )

    original_id = existing.id

    config = make_stage_config(
        project.id,
        ConfigProjectStage.CONSTRUCTION,
        enabled=True,
        num_reports_required=6,
        frequency="MONTHLY",
    )

    db = FakeSession(
        execute_returns=[
            [existing],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    assert existing.id == original_id
    assert existing.stage == ProjectStage.CONSTRUCTION
    assert existing.sequence == 3
    assert existing.num_reports_required == 6
    assert existing.frequency == "MONTHLY"

    # The existing ORM object may be re-added to the session.
    # Verify that no replacement/new instance was created.
    created = [
        obj
        for obj in db.added_of_type(ProjectStageInstance)
        if obj is not existing
    ]
    assert created == []


# ---------------------------------------------------------------------------
# 7. Missing configured stage -> no instance created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_or_missing_stage_does_not_create_instance():
    project = make_project()

    # No existing stage instances.
    #
    # BUSINESS_CASE is explicitly disabled.
    # DESIGN and CONSTRUCTION are omitted.
    config = make_stage_config(
        project.id,
        ConfigProjectStage.BUSINESS_CASE,
        enabled=False,
    )

    db = FakeSession(
        execute_returns=[
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    assert db.added_of_type(ProjectStageInstance) == []


# ---------------------------------------------------------------------------
# 8. Multiple enabled stages -> all receive persistent instances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_enabled_stages_create_expected_instances():
    project = make_project()

    configs = [
        make_stage_config(
            project.id,
            ConfigProjectStage.BUSINESS_CASE,
            enabled=True,
            num_reports_required=1,
            frequency="ANNUAL",
        ),
        make_stage_config(
            project.id,
            ConfigProjectStage.DESIGN,
            enabled=True,
            num_reports_required=2,
            frequency="QUARTERLY",
        ),
        make_stage_config(
            project.id,
            ConfigProjectStage.CONSTRUCTION,
            enabled=True,
            num_reports_required=3,
            frequency="MONTHLY",
        ),
    ]

    db = FakeSession(
        execute_returns=[
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=configs,
    )

    created = db.added_of_type(ProjectStageInstance)

    assert len(created) == 3

    by_stage = {
        instance.stage: instance
        for instance in created
    }

    assert by_stage[ProjectStage.BUSINESS_CASE].sequence == 1
    assert by_stage[ProjectStage.DESIGN].sequence == 2
    assert by_stage[ProjectStage.CONSTRUCTION].sequence == 3

    assert (
        by_stage[ProjectStage.BUSINESS_CASE].num_reports_required
        == 1
    )
    assert (
        by_stage[ProjectStage.DESIGN].num_reports_required
        == 2
    )
    assert (
        by_stage[ProjectStage.CONSTRUCTION].num_reports_required
        == 3
    )


# ---------------------------------------------------------------------------
# 9. Existing stage + newly enabled stage -> preserve + create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_and_new_stage_are_synchronized_together():
    project = make_project()

    existing_business_case = make_stage_instance(
        project.id,
        ProjectStage.BUSINESS_CASE,
        sequence=1,
        num_reports_required=1,
        frequency="ANNUAL",
    )

    original_id = existing_business_case.id

    configs = [
        make_stage_config(
            project.id,
            ConfigProjectStage.BUSINESS_CASE,
            enabled=True,
            num_reports_required=5,
            frequency="MONTHLY",
        ),
        make_stage_config(
            project.id,
            ConfigProjectStage.DESIGN,
            enabled=True,
            num_reports_required=2,
            frequency="QUARTERLY",
        ),
    ]

    db = FakeSession(
        execute_returns=[
            [existing_business_case],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=configs,
    )

    created = [
        obj
        for obj in db.added_of_type(ProjectStageInstance)
        if obj is not existing_business_case
    ]

    assert len(created) == 1

    new_design = created[0]

    assert new_design.stage == ProjectStage.DESIGN
    assert new_design.id != original_id

    assert existing_business_case.id == original_id
    assert existing_business_case.num_reports_required == 5
    assert existing_business_case.frequency == "MONTHLY"


# ---------------------------------------------------------------------------
# 10. Recurring instance is preserved / created by recurring lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recurring_instance_is_preserved_when_already_exists():
    project = make_project()

    recurring = make_stage_instance(
        project.id,
        ProjectStage.RECURRING,
        sequence=0,
    )

    original_id = recurring.id

    # _sync_project_stage_instances() deliberately handles only the
    # configurable stages. RECURRING must therefore not be touched here.
    configs = []

    db = FakeSession(
        execute_returns=[
            [recurring],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=configs,
    )

    assert recurring.id == original_id
    assert recurring.stage == ProjectStage.RECURRING

    assert db.added_of_type(ProjectStageInstance) == []


# ---------------------------------------------------------------------------
# 11. Retained disabled stage must not regain access through assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_stage_assignments_are_not_created_during_sync():
    """
    Regression test for the legacy member_accesses path.

    _sync_project_stage_instances() itself only manages lifecycle and
    deactivation. It must never create PROJECT_EDITOR / PROJECT_VIEWER
    assignments for a disabled retained stage.
    """

    project = make_project()

    retained_disabled_stage = make_stage_instance(
        project.id,
        ProjectStage.DESIGN,
        sequence=2,
    )

    config = make_stage_config(
        project.id,
        ConfigProjectStage.DESIGN,
        enabled=False,
    )

    db = FakeSession(
        execute_returns=[
            [retained_disabled_stage],
            [],
            [],
        ]
    )

    await _sync_project_stage_instances(
        db,
        project=project,
        stage_configs=[config],
    )

    # Lifecycle sync must not create any stage UserRole rows.
    assert db.added_of_type(UserRole) == []

    # The historical instance remains.
    assert retained_disabled_stage.id is not None