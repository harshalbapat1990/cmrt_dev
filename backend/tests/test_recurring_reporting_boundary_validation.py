from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from crud.project import _validate_recurring, update_project
from models.project import ProjectClass
from schemas.project import ProjectUpdate


@pytest.mark.asyncio
async def test_recurring_project_creation_requires_at_least_one_reporting_boundary():
    payload = SimpleNamespace(
        first_submission_month=date(2026, 1, 1),
        construction_start_date=None,
        construction_end_date=None,
        commencement_of_operations=None,
        operational_life_years=None,
        reporting_boundaries=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await _validate_recurring(payload)

    assert exc_info.value.status_code == 400
    assert "At least one reporting boundary" in exc_info.value.detail


@pytest.mark.asyncio
async def test_recurring_project_update_cannot_leave_zero_reporting_boundaries():
    project = SimpleNamespace(
        project_class=ProjectClass.RECURRING,
        reporting_boundaries=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_project(None, project, ProjectUpdate(project_name="Updated name"))

    assert exc_info.value.status_code == 400
    assert "At least one reporting boundary" in exc_info.value.detail


@pytest.mark.asyncio
async def test_recurring_project_update_cannot_remove_its_final_boundary():
    project = SimpleNamespace(
        project_class=ProjectClass.RECURRING,
        reporting_boundaries=[SimpleNamespace(id="boundary-1")],
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_project(None, project, ProjectUpdate(reporting_boundaries=[]))

    assert exc_info.value.status_code == 400
    assert "At least one reporting boundary" in exc_info.value.detail
