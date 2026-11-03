"""PostgreSQL-specific checks for active revision-scoped metric selection."""

from decimal import Decimal
from uuid import uuid4

import pytest

from crud.background_grade_metrics import (
    background_grade_metric_to_natural_key,
    get_background_grade_metric_by_natural_key,
    list_background_grade_metrics,
)
from models.background_grade_metrics import BackgroundGradeMetric
from models.dataset_revisions import DatasetRevision
from models.grade_definitions import GradeDefinition
from models.metric_types import MetricType


@pytest.mark.integration
@pytest.mark.asyncio
async def test_natural_key_returns_active_metric_only_in_selected_revision(postgres_session):
    revision_id = uuid4()
    other_revision_id = uuid4()
    metric_type_id = uuid4()
    code = f"integration_{uuid4().hex}"
    grade_id = 30000 + (uuid4().int % 2000)
    postgres_session.add_all([
        DatasetRevision(id=revision_id, name=f"revision_{uuid4().hex}", scope_type="DEFAULT"),
        DatasetRevision(id=other_revision_id, name=f"revision_{uuid4().hex}", scope_type="DEFAULT"),
        MetricType(id=metric_type_id, code=code, name=code),
        GradeDefinition(id=grade_id, name=f"Grade {grade_id}"),
    ])
    await postgres_session.flush()

    shared_key = {
        "dataset_revision_id": revision_id,
        "grade_id": grade_id,
        "metric_type_id": metric_type_id,
        "value": Decimal("1.4"),
    }
    old = BackgroundGradeMetric(**shared_key, is_active=False)
    active = BackgroundGradeMetric(**{**shared_key, "value": Decimal("2.4")}, is_active=True)
    wrong_revision = BackgroundGradeMetric(
        **{**shared_key, "dataset_revision_id": other_revision_id}, is_active=True
    )
    postgres_session.add_all([old, active, wrong_revision])
    await postgres_session.flush()

    found = await get_background_grade_metric_by_natural_key(
        postgres_session,
        revision_id,
        background_grade_metric_to_natural_key(active),
    )
    listed = await list_background_grade_metrics(
        postgres_session,
        dataset_revision_id=revision_id,
        grade_id=grade_id,
        metric_type_codes=[code],
    )

    assert found.id == active.id
    assert found.value == Decimal("2.4")
    assert [row["id"] for row in listed] == [active.id]
