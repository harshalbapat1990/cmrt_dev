from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from crud import project_reporting_submission as submissions
from models.project import ProjectClass
from models.project_reporting_submission import ProjectReportingSubmission
from models.project_stage_config import ReportFrequency


class _Scalars:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value

    def all(self):
        return self.value or []


class _Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return _Scalars(self.value)

    def scalar_one_or_none(self):
        return self.value


class _Db:
    def __init__(self, results):
        self.results = list(results)
        self.added = []

    async def execute(self, _query):
        return _Result(self.results.pop(0))

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def refresh(self, _value):
        return None


@pytest.mark.asyncio
async def test_seed_first_period_uses_first_submission_month_and_is_idempotent():
    project_id = uuid4()
    stage_instance_id = uuid4()
    stage_instance = SimpleNamespace(
        id=stage_instance_id,
        project_id=project_id,
        approval_status="draft",
    )
    project = SimpleNamespace(
        id=project_id,
        first_submission_month=date(2026, 3, 19),
        construction_start_date=None,
    )
    stage_config = SimpleNamespace(frequency=ReportFrequency.MONTHLY)
    db = _Db([stage_instance, project, stage_config, [], None])

    period = await submissions.seed_first_period(db, stage_instance_id)

    assert period is db.added[0]
    assert period.project_id == project_id
    assert period.stage_instance_id == stage_instance_id
    assert period.frequency == "MONTHLY"
    assert period.period_label == "Mar 2026"
    assert period.period_start_date == date(2026, 3, 1)
    assert period.period_end_date == date(2026, 3, 31)
    assert period.status == "in_progress"

    existing_period = SimpleNamespace(status="in_progress")
    already_seeded_db = _Db([stage_instance, project, stage_config, [existing_period]])
    result = await submissions.seed_first_period(already_seeded_db, stage_instance_id)

    assert result is None
    assert already_seeded_db.added == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("project_class", "expected_stage"),
    [
        (ProjectClass.RECURRING, "RECURRING"),
        (ProjectClass.LARGE, "CONSTRUCTION"),
    ],
)
async def test_generated_periods_are_linked_to_the_right_stage_instance(project_class, expected_stage):
    project_id = uuid4()
    stage_instance_id = uuid4()
    config = SimpleNamespace(frequency=ReportFrequency.MONTHLY)
    stage_instance = SimpleNamespace(id=stage_instance_id, stage=expected_stage)
    db = _Db([config, stage_instance, None, None])
    project = SimpleNamespace(
        id=project_id,
        project_class=project_class,
        first_submission_month=date(2026, 3, 1),
        construction_start_date=None,
    )

    await submissions.generate_submissions_for_project(db, project, periods=2)

    assert len(db.added) == 2
    assert all(isinstance(period, ProjectReportingSubmission) for period in db.added)
    assert all(period.stage_instance_id == stage_instance_id for period in db.added)
    assert [period.period_label for period in db.added] == ["Mar 2026", "Apr 2026"]


@pytest.mark.asyncio
async def test_recurring_project_creation_seeds_a_period_without_opt_in(monkeypatch):
    from routers import project as project_router

    project_id = uuid4()
    proponent_org_id = uuid4()
    user_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        project_name="Recurring test project",
        project_class=ProjectClass.RECURRING,
    )
    principal = SimpleNamespace(user_id=user_id, organization_id=proponent_org_id)
    db = SimpleNamespace(commit=AsyncMock())
    payload = SimpleNamespace(proponent_org_id=proponent_org_id)

    get_roles = AsyncMock(return_value={"ORG_ADMIN"})
    create = AsyncMock(return_value=project)
    seed = AsyncMock()
    generate = AsyncMock()
    audit = AsyncMock()
    get_project = AsyncMock(return_value=project)
    monkeypatch.setattr(project_router, "get_org_scoped_role_names", get_roles)
    monkeypatch.setattr(project_router, "create_project", create)
    monkeypatch.setattr(project_router, "seed_recurring_first_period", seed)
    monkeypatch.setattr(project_router, "generate_submissions_for_project", generate)
    monkeypatch.setattr(project_router, "write_audit_event", audit)
    monkeypatch.setattr(project_router, "get_project", get_project)

    await project_router.create_new_project(
        payload,
        auto_generate_submissions=False,
        periods=12,
        principal=principal,
        db=db,
    )

    seed.assert_awaited_once_with(db, project_id)
    generate.assert_not_awaited()
