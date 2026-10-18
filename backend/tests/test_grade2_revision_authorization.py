from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.security import Principal, get_current_principal
from routers import grade2_b4_replacement_calculations as b4_router
from routers import grade2_calculations as grade2_router
from services.grade2_component_calculations import Grade2CalculationRequest
from services.grade2_b4_replacement_calculations import Grade2B4ReplacementRequest


def _principal() -> Principal:
    return Principal(user_id=uuid4(), email="reader@example.com")


def test_grade2_calculation_routes_require_authenticated_principal():
    for router in (grade2_router.router, b4_router.router):
        route = next(route for route in router.routes if route.path.endswith("/calculate"))
        assert any(dependency.call is get_current_principal for dependency in route.dependant.dependencies)


@pytest.mark.asyncio
async def test_grade2_requires_project_or_revision_selector():
    payload = Grade2CalculationRequest(
        jurisdiction="Australia",
        emissions_category="Materials",
        emissions_sub_category="Concrete",
        emissions_source="Ready mix",
        quantity=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        await grade2_router.calculate_grade2_emissions(payload, object(), _principal())
    assert exc_info.value.status_code == 400
    assert "project_id or dataset_revision_id is required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_grade2_explicit_revision_is_authorized_and_used(monkeypatch):
    revision_id = uuid4()
    authorized = []
    calculated = []

    async def authorize(_db, _principal, requested_id):
        authorized.append(requested_id)

    async def calculate(_db, payload):
        calculated.append(payload.dataset_revision_id)
        return SimpleNamespace(total_emissions_tco2e=1)

    monkeypatch.setattr(grade2_router, "assert_dataset_revision_read_permission", authorize)
    monkeypatch.setattr(grade2_router.calculator, "calculate", calculate)
    payload = Grade2CalculationRequest(
        jurisdiction="Australia",
        emissions_category="Materials",
        emissions_sub_category="Concrete",
        emissions_source="Ready mix",
        quantity=1,
        dataset_revision_id=revision_id,
    )
    await grade2_router.calculate_grade2_emissions(payload, object(), _principal())
    assert authorized == [revision_id]
    assert calculated == [revision_id]


@pytest.mark.asyncio
async def test_grade2_project_binding_is_authorized_and_used(monkeypatch):
    project_id, revision_id = uuid4(), uuid4()
    calculated = []

    async def authorize(_db, _principal, requested_project, requested_revision=None):
        assert requested_project == project_id
        assert requested_revision is None
        return revision_id

    async def calculate(_db, payload):
        calculated.append(payload.dataset_revision_id)
        return SimpleNamespace(total_emissions_tco2e=1)

    monkeypatch.setattr(grade2_router, "assert_project_dataset_revision_read_permission", authorize)
    monkeypatch.setattr(grade2_router.calculator, "calculate", calculate)
    payload = Grade2CalculationRequest(
        jurisdiction="Australia",
        emissions_category="Materials",
        emissions_sub_category="Concrete",
        emissions_source="Ready mix",
        quantity=1,
        project_id=project_id,
    )
    await grade2_router.calculate_grade2_emissions(payload, object(), _principal())
    assert calculated == [revision_id]


@pytest.mark.asyncio
async def test_b4_calculation_uses_authorized_project_revision(monkeypatch):
    project_id, revision_id = uuid4(), uuid4()
    calculated = []

    async def authorize(_db, _principal, requested_project, requested_revision=None):
        assert requested_project == project_id
        assert requested_revision is None
        return revision_id

    async def calculate(_db, payload):
        calculated.append(payload.dataset_revision_id)
        return SimpleNamespace(total_emissions_tco2e=1)

    monkeypatch.setattr(b4_router, "assert_project_dataset_revision_read_permission", authorize)
    monkeypatch.setattr(b4_router.calculator, "calculate", calculate)
    payload = Grade2B4ReplacementRequest(
        project_id=project_id,
        emissions_category="Materials",
        emissions_sub_category="Concrete",
        emissions_source="Ready mix",
        quantity=1,
        life_years=10,
    )
    await b4_router.calculate_b4_replacement_emissions(payload, object(), _principal())
    assert calculated == [revision_id]


@pytest.mark.asyncio
async def test_grade2_metric_lookup_is_revision_scoped():
    revision_id = uuid4()

    class FakeResult:
        def all(self):
            return [
                SimpleNamespace(metric_type_code="emission_intensity_a1_a3", value=2, uom="m3", source_comments="source"),
                SimpleNamespace(metric_type_code="emission_intensity_a4", value=3, uom="m3", source_comments="source"),
                SimpleNamespace(metric_type_code="emission_intensity_a5", value=4, uom="m3", source_comments="source"),
                SimpleNamespace(metric_type_code="carbon_storage", value=-1, uom="m3", source_comments="source"),
            ]

    class FakeSession:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return FakeResult()

    from services.grade2_component_calculations import Grade2ComponentCalculator

    db = FakeSession()
    request = Grade2CalculationRequest(
        jurisdiction="Australia",
        emissions_category="Materials",
        emissions_sub_category="Concrete",
        emissions_source="Ready mix",
        quantity=2,
        dataset_revision_id=revision_id,
    )
    lookup = await Grade2ComponentCalculator()._fetch_lookup(db, request)
    compiled = db.statement.compile()
    assert revision_id in compiled.params.values()
    assert "dataset_revision_id" in str(compiled)
    assert lookup == {
        "factor_a1_a3": 2.0,
        "factor_a4": 3.0,
        "factor_a5": 4.0,
        "carbon_storage": -1.0,
        "uom": "m3",
        "source_comments": "source",
    }
