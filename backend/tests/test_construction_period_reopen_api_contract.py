from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_request_reopen_api_requires_reason(client):
    response = await client.post(f"/api/construction-periods/{uuid4()}/request-reopen")

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.asyncio
async def test_request_reopen_returns_404_when_period_does_not_exist(monkeypatch):
    from fastapi import HTTPException
    from routers import construction_periods as router

    async def no_period(_db, _period_id):
        return None

    # Keep the route's real 404 guard in the test. Replacing
    # _get_period_or_404 itself with a None-returning stub bypasses that guard
    # and makes the route dereference period.project_id instead.
    monkeypatch.setattr(router, "get_construction_period", no_period)

    with pytest.raises(HTTPException) as exc:
        await router.request_reopen_period(
            period_id=uuid4(),
            reopen_reason="Please correct the report",
            principal=type("PrincipalStub", (), {"user_id": uuid4()})(),
            db=object(),
        )

    assert exc.value.status_code == 404
