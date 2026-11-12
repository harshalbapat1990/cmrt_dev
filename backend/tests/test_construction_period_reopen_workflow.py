from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


class _Db:
    def __init__(self):
        self.commits = 0
        self.refreshed = []

    async def commit(self):
        self.commits += 1

    async def refresh(self, value):
        self.refreshed.append(value)


def _period(status="approved"):
    return SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        stage_instance_id=uuid4(),
        status=status,
        reopen_requested_by=None,
        reopen_requested_at=None,
        reopen_reason=None,
        decision_by=None,
        decision_at=None,
        rejection_reason=None,
    )


def _status_setter():
    async def set_status(_db, period, status, **fields):
        period.status = status
        for key, value in fields.items():
            setattr(period, key, value)
        return period

    return set_status


@pytest.mark.asyncio
async def test_request_reopen_records_reason_actor_status_and_event(monkeypatch):
    from routers import construction_periods as router

    period = _period()
    principal = SimpleNamespace(user_id=uuid4())
    db = _Db()
    events = []

    async def get_period(_db, _period_id):
        return period

    async def require_edit(*_args, **_kwargs):
        return None

    async def record(_db, **event):
        events.append(event)

    monkeypatch.setattr(router, "_get_period_or_404", get_period)
    monkeypatch.setattr(router, "require_stage_access", require_edit)
    monkeypatch.setattr(router, "set_period_status", _status_setter())
    monkeypatch.setattr(router, "record_event", record)

    result = await router.request_reopen_period(
        period_id=period.id,
        reopen_reason="Correct the submitted activity values",
        principal=principal,
        db=db,
    )

    assert result is period
    assert period.status == "reopen_requested"
    assert period.reopen_reason == "Correct the submitted activity values"
    assert period.reopen_requested_by == principal.user_id
    assert isinstance(period.reopen_requested_at, datetime)
    assert events == [{
        "stage_instance_id": period.stage_instance_id,
        "project_id": period.project_id,
        "event_type": "reopen_requested",
        "performed_by": principal.user_id,
        "from_status": "approved",
        "to_status": "reopen_requested",
        "justification": "Correct the submitted activity values",
        "submission_period_id": period.id,
    }]
    assert db.commits == 1
    assert db.refreshed == [period]


@pytest.mark.asyncio
async def test_request_reopen_rejects_non_approved_period_without_writes(monkeypatch):
    from routers import construction_periods as router

    period = _period(status="awaiting_approval")
    db = _Db()
    calls = []

    async def get_period(_db, _period_id):
        return period

    async def require_edit(*_args, **_kwargs):
        return None

    async def change_status(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(router, "_get_period_or_404", get_period)
    monkeypatch.setattr(router, "require_stage_access", require_edit)
    monkeypatch.setattr(router, "set_period_status", change_status)

    with pytest.raises(HTTPException) as exc:
        await router.request_reopen_period(
            period_id=period.id,
            reopen_reason="Please reopen",
            principal=SimpleNamespace(user_id=uuid4()),
            db=db,
        )

    assert exc.value.status_code == 400
    assert period.status == "awaiting_approval"
    assert calls == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_request_reopen_propagates_stage_access_denial(monkeypatch):
    from routers import construction_periods as router

    period = _period()
    db = _Db()

    async def get_period(_db, _period_id):
        return period

    async def deny_access(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="No stage edit access")

    monkeypatch.setattr(router, "_get_period_or_404", get_period)
    monkeypatch.setattr(router, "require_stage_access", deny_access)

    with pytest.raises(HTTPException) as exc:
        await router.request_reopen_period(
            period_id=period.id,
            reopen_reason="Please reopen",
            principal=SimpleNamespace(user_id=uuid4()),
            db=db,
        )

    assert exc.value.status_code == 403
    assert period.status == "approved"
    assert db.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_name", "decision", "expected_status", "expected_event"),
    [
        ("approve_reopen_period", {}, "in_progress", "reopen_approved"),
        ("reject_reopen_period", {"rejection_reason": "Insufficient detail"}, "approved", "reopen_rejected"),
    ],
)
async def test_admin_reopen_decisions_transition_and_audit(
    monkeypatch, handler_name, decision, expected_status, expected_event
):
    from routers import construction_periods as router

    period = _period(status="reopen_requested")
    principal = SimpleNamespace(user_id=uuid4())
    db = _Db()
    events = []

    async def get_period(_db, _period_id):
        return period

    async def require_edit(*_args, **_kwargs):
        return None

    async def record(_db, **event):
        events.append(event)

    monkeypatch.setattr(router, "_get_period_or_404", get_period)
    monkeypatch.setattr(router, "require_stage_access", require_edit)
    monkeypatch.setattr(router, "set_period_status", _status_setter())
    monkeypatch.setattr(router, "record_event", record)

    handler = getattr(router, handler_name)
    result = await handler(
        period_id=period.id,
        principal=principal,
        db=db,
        **decision,
    )

    assert result is period
    assert period.status == expected_status
    assert period.decision_by == principal.user_id
    assert isinstance(period.decision_at, datetime)
    assert events[0]["event_type"] == expected_event
    assert events[0]["from_status"] == "reopen_requested"
    assert events[0]["to_status"] == expected_status
    assert events[0]["submission_period_id"] == period.id
    assert db.commits == 1
    assert db.refreshed == [period]
